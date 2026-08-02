import json
import os
import random
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands


TOKEN_FILE = Path("token.txt")
HISTORY_FILE = Path("lottery_history.json")


def read_token() -> str:
    """Railwayでは環境変数TOKEN、ローカルではtoken.txtを使用する。"""
    token = os.getenv("TOKEN", "").strip()

    if token:
        return token

    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()

        if token:
            return token

    raise FileNotFoundError(
        "TOKEN環境変数またはtoken.txtを設定してください。"
    )


def split_lines(text: str) -> list[str]:
    return [
        item.strip()
        for item in text.replace(",", "\n").splitlines()
        if item.strip()
    ]


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []

    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history: list[dict]) -> None:
    with HISTORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)


def make_setup_embed(view: "LotterySetupView") -> discord.Embed:
    lottery_name_status = (
        f"✅ {view.lottery_name}" if view.lottery_name else "❌ 未入力"
    )
    participant_status = (
        f"✅ {len(view.participants)}人入力済み"
        if view.participants
        else "❌ 未入力"
    )
    prize_status = (
        f"✅ {len(view.prizes)}個入力済み"
        if view.prizes
        else "❌ 未入力"
    )
    count_status = (
        f"✅ {view.winner_count}人"
        if view.winner_count is not None
        else "❌ 未入力"
    )

    title = view.lottery_name or "ランダム抽選"

    embed = discord.Embed(
        title=f"🎲 {title}",
        description=(
            "下のボタンから抽選内容を入力してください。\n"
            "すべて入力したら「抽選開始」を押します。"
        ),
    )
    embed.add_field(name="📛 抽選名", value=lottery_name_status, inline=False)
    embed.add_field(name="👥 参加者", value=participant_status, inline=False)
    embed.add_field(name="🎁 景品", value=prize_status, inline=False)
    embed.add_field(name="🔢 当選人数", value=count_status, inline=False)
    return embed


class LotteryNameModal(discord.ui.Modal, title="抽選名を入力"):
    lottery_name_input = discord.ui.TextInput(
        label="抽選名",
        placeholder="例：第1回プレゼント抽選会",
        required=True,
        max_length=100,
    )

    def __init__(self, setup_view: "LotterySetupView") -> None:
        super().__init__()
        self.setup_view = setup_view

        if setup_view.lottery_name:
            self.lottery_name_input.default = setup_view.lottery_name

    async def on_submit(self, interaction: discord.Interaction) -> None:
        lottery_name = str(self.lottery_name_input).strip()

        if not lottery_name:
            await interaction.response.send_message(
                "抽選名を入力してください。",
                ephemeral=True,
            )
            return

        self.setup_view.lottery_name = lottery_name
        await interaction.response.edit_message(
            embed=make_setup_embed(self.setup_view),
            view=self.setup_view,
        )


class ParticipantsModal(discord.ui.Modal, title="参加者を入力"):
    participants_input = discord.ui.TextInput(
        label="参加者",
        style=discord.TextStyle.paragraph,
        placeholder="A\nB\nC\nD",
        required=True,
        max_length=4000,
    )

    def __init__(self, setup_view: "LotterySetupView") -> None:
        super().__init__()
        self.setup_view = setup_view

        if setup_view.participants:
            self.participants_input.default = "\n".join(setup_view.participants)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        participants = list(dict.fromkeys(split_lines(str(self.participants_input))))

        if not participants:
            await interaction.response.send_message(
                "参加者を1人以上入力してください。",
                ephemeral=True,
            )
            return

        self.setup_view.participants = participants
        await interaction.response.edit_message(
            embed=make_setup_embed(self.setup_view),
            view=self.setup_view,
        )


class PrizesModal(discord.ui.Modal, title="景品を入力"):
    prizes_input = discord.ui.TextInput(
        label="景品",
        style=discord.TextStyle.paragraph,
        placeholder="Amazonギフト券\nDiscord Nitro\nスタバカード",
        required=True,
        max_length=4000,
    )

    def __init__(self, setup_view: "LotterySetupView") -> None:
        super().__init__()
        self.setup_view = setup_view

        if setup_view.prizes:
            self.prizes_input.default = "\n".join(setup_view.prizes)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        prizes = split_lines(str(self.prizes_input))

        if not prizes:
            await interaction.response.send_message(
                "景品を1個以上入力してください。",
                ephemeral=True,
            )
            return

        self.setup_view.prizes = prizes
        await interaction.response.edit_message(
            embed=make_setup_embed(self.setup_view),
            view=self.setup_view,
        )


class WinnerCountModal(discord.ui.Modal, title="当選人数を入力"):
    winner_count_input = discord.ui.TextInput(
        label="当選人数",
        placeholder="例：3",
        required=True,
        max_length=3,
    )

    def __init__(self, setup_view: "LotterySetupView") -> None:
        super().__init__()
        self.setup_view = setup_view

        if setup_view.winner_count is not None:
            self.winner_count_input.default = str(setup_view.winner_count)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            winner_count = int(str(self.winner_count_input).strip())
        except ValueError:
            await interaction.response.send_message(
                "当選人数は数字で入力してください。",
                ephemeral=True,
            )
            return

        if winner_count < 1:
            await interaction.response.send_message(
                "当選人数は1人以上にしてください。",
                ephemeral=True,
            )
            return

        self.setup_view.winner_count = winner_count
        await interaction.response.edit_message(
            embed=make_setup_embed(self.setup_view),
            view=self.setup_view,
        )


class LotterySetupView(discord.ui.View):
    def __init__(self, owner_id: int) -> None:
        super().__init__(timeout=600)

        self.owner_id = owner_id
        self.lottery_name: str = ""
        self.participants: list[str] = []
        self.prizes: list[str] = []
        self.winner_count: int | None = None
        self.finished = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "この抽選画面は、抽選を開始した管理者だけ操作できます。",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="抽選名入力",
        emoji="📛",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def lottery_name_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_modal(LotteryNameModal(self))

    @discord.ui.button(
        label="参加者入力",
        emoji="👥",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def participants_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_modal(ParticipantsModal(self))

    @discord.ui.button(
        label="景品入力",
        emoji="🎁",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def prizes_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_modal(PrizesModal(self))

    @discord.ui.button(
        label="当選人数入力",
        emoji="🔢",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def winner_count_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_modal(WinnerCountModal(self))

    @discord.ui.button(
        label="抽選開始",
        emoji="🎲",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def start_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.finished:
            await interaction.response.send_message(
                "この抽選はすでに実行されています。",
                ephemeral=True,
            )
            return

        if not self.lottery_name:
            await interaction.response.send_message(
                "抽選名を入力してください。",
                ephemeral=True,
            )
            return

        if not self.participants:
            await interaction.response.send_message(
                "参加者を入力してください。",
                ephemeral=True,
            )
            return

        if not self.prizes:
            await interaction.response.send_message(
                "景品を入力してください。",
                ephemeral=True,
            )
            return

        if self.winner_count is None:
            await interaction.response.send_message(
                "当選人数を入力してください。",
                ephemeral=True,
            )
            return

        if self.winner_count > len(self.prizes):
            await interaction.response.send_message(
                "景品数が当選人数より少ないです。",
                ephemeral=True,
            )
            return

        self.finished = True

        # 参加者数が足りる場合は重複なし。
        # 当選人数が参加者数を超える場合だけ、同じ人の重複当選を許可する。
        duplicate_winners = self.winner_count > len(self.participants)

        if duplicate_winners:
            winners = random.choices(
                self.participants,
                k=self.winner_count,
            )
        else:
            winners = random.sample(
                self.participants,
                self.winner_count,
            )

        selected_prizes = random.sample(self.prizes, self.winner_count)
        random.shuffle(selected_prizes)
        results = list(zip(winners, selected_prizes))

        result_lines = [
            f"**{index}. {winner}**\n└ 🎁 {prize}"
            for index, (winner, prize) in enumerate(results, start=1)
        ]

        result_embed = discord.Embed(
            title=f"🎉 {self.lottery_name}",
            description="\n\n".join(result_lines),
        )
        result_embed.add_field(
            name="参加者数",
            value=str(len(self.participants)),
            inline=True,
        )
        result_embed.add_field(
            name="当選人数",
            value=str(self.winner_count),
            inline=True,
        )

        result_embed.add_field(
            name="重複当選",
            value="あり（参加者不足）" if duplicate_winners else "なし",
            inline=True,
        )

        unused_prizes = len(self.prizes) - self.winner_count
        if unused_prizes > 0:
            result_embed.add_field(
                name="未使用の景品",
                value=f"{unused_prizes}個",
                inline=True,
            )

        result_embed.set_footer(
            text=f"実行者：{interaction.user.display_name}"
        )

        history = load_history()
        history.append(
            {
                "date": datetime.now().isoformat(timespec="seconds"),
                "lottery_name": self.lottery_name,
                "executor": str(interaction.user),
                "participants": self.participants,
                "winner_count": self.winner_count,
                "duplicate_winners": duplicate_winners,
                "prizes": self.prizes,
                "results": [
                    {"winner": winner, "prize": prize}
                    for winner, prize in results
                ],
            }
        )
        save_history(history)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="✅ 抽選完了",
                description="抽選結果をチャンネルに送信しました。",
            ),
            view=self,
        )

        await interaction.followup.send(
            embed=result_embed,
            ephemeral=False,
        )

        self.stop()

    @discord.ui.button(
        label="キャンセル",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        row=2,
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            embed=discord.Embed(title="🗑️ 抽選をキャンセルしました"),
            view=self,
        )
        self.stop()


class LotteryClient(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        synced = await self.tree.sync()
        print(f"{len(synced)}個のコマンドを同期しました。")


client = LotteryClient()


@client.event
async def on_ready() -> None:
    print(f"{client.user}として起動しました。")


@client.tree.command(
    name="抽選",
    description="ボタン画面から抽選内容を設定します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def lottery(interaction: discord.Interaction) -> None:
    view = LotterySetupView(interaction.user.id)
    await interaction.response.send_message(
        embed=make_setup_embed(view),
        view=view,
        ephemeral=True,
    )


@client.tree.command(
    name="抽選履歴",
    description="最近の抽選履歴を表示します",
)
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def lottery_history(interaction: discord.Interaction) -> None:
    history = load_history()

    if not history:
        await interaction.response.send_message(
            "抽選履歴はまだありません。",
            ephemeral=True,
        )
        return

    recent_history = history[-5:]
    sections = []

    for item in reversed(recent_history):
        result_text = "\n".join(
            f"・{result['winner']} → {result['prize']}"
            for result in item.get("results", [])
        )

        lottery_name = item.get("lottery_name", "名称なし")

        sections.append(
            f"**🎲 {lottery_name}**\n"
            f"日時：{item.get('date', '不明')}\n"
            f"実行者：{item.get('executor', '不明')}\n"
            f"{result_text}"
        )

    embed = discord.Embed(
        title="📜 最近の抽選履歴",
        description="\n\n".join(sections),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )


@lottery.error
@lottery_history.error
async def command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        message = "このコマンドは管理者だけ使用できます。"
    else:
        message = f"エラーが発生しました：{error}"

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


client.run(read_token())