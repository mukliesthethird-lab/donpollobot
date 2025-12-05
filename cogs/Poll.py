import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ==========================================
# CONSTANTS & CONFIG
# ==========================================
POLL_FILE = "polls.json"

# ==========================================
# POLL MANAGER (PERSISTENCE)
# ==========================================
class PollManager:
    def __init__(self):
        self.polls = {}
        self.load_polls()

    def load_polls(self):
        if os.path.exists(POLL_FILE):
            try:
                with open(POLL_FILE, "r") as f:
                    data = json.load(f)
                    # Convert timestamp strings back to datetime objects if needed
                    # But we will store them as timestamps (float) for simplicity
                    self.polls = data
            except Exception as e:
                print(f"❌ Failed to load polls: {e}")
                self.polls = {}

    def save_polls(self):
        try:
            with open(POLL_FILE, "w") as f:
                json.dump(self.polls, f, indent=4)
        except Exception as e:
            print(f"❌ Failed to save polls: {e}")

    def create_poll(self, message_id: int, channel_id: int, guild_id: int, question: str, options: List[str], end_time: float, author_id: int, author_name: str):
        self.polls[str(message_id)] = {
            "channel_id": channel_id,
            "guild_id": guild_id,
            "question": question,
            "options": options,
            "votes": {},  # user_id: option_index
            "end_time": end_time,
            "author_id": author_id,
            "author_name": author_name,
            "active": True
        }
        self.save_polls()

    def get_poll(self, message_id: int):
        return self.polls.get(str(message_id))

    def add_vote(self, message_id: int, user_id: int, option_index: int) -> bool:
        """Returns True if vote changed/added, False if already voted same."""
        poll = self.get_poll(message_id)
        if not poll:
            return False
        
        user_key = str(user_id)
        if poll["votes"].get(user_key) == option_index:
            return False
        
        poll["votes"][user_key] = option_index
        self.save_polls()
        return True

    def end_poll(self, message_id: int):
        if str(message_id) in self.polls:
            self.polls[str(message_id)]["active"] = False
            self.save_polls()
            # We don't delete immediately to allow "view results" after end, 
            # but for this logic we can just mark inactive.
            # Or we can delete it to clean up. Let's delete it to keep file small.
            del self.polls[str(message_id)]
            self.save_polls()

# ==========================================
# UI COMPONENTS
# ==========================================
class PollButton(discord.ui.Button):
    def __init__(self, index: int, label: str):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=label[:80], # Discord limit
            custom_id=f"poll_btn_{index}"
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: PollView = self.view
        if not view.manager.get_poll(view.message_id):
            await interaction.response.send_message("❌ Poll ini sudah tidak aktif.", ephemeral=True)
            return

        changed = view.manager.add_vote(view.message_id, interaction.user.id, self.index)
        
        if changed:
            await interaction.response.send_message(f"✅ Kamu memilih: **{self.label}**", ephemeral=True)
            await view.update_message()
        else:
            await interaction.response.send_message(f"ℹ️ Kamu sudah memilih **{self.label}** sebelumnya.", ephemeral=True)

class PollView(discord.ui.View):
    def __init__(self, manager: PollManager, message_id: int, options: List[str]):
        super().__init__(timeout=None) # Persistent view
        self.manager = manager
        self.message_id = message_id
        self.options = options
        
        for i, option in enumerate(options):
            self.add_item(PollButton(i, option))

    async def update_message(self):
        # Logic to update the embed with new vote counts
        poll = self.manager.get_poll(self.message_id)
        if not poll:
            return

        # Calculate votes
        vote_counts = [0] * len(self.options)
        total_votes = 0
        for vote_idx in poll["votes"].values():
            if 0 <= vote_idx < len(vote_counts):
                vote_counts[vote_idx] += 1
                total_votes += 1

        # Rebuild Embed
        embed = discord.Embed(
            title="📊 Polling Berlangsung",
            description=f"**{poll['question']}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        end_time = datetime.fromtimestamp(poll['end_time'])
        embed.add_field(
            name="⏱️ Berakhir",
            value=f"<t:{int(poll['end_time'])}:R>",
            inline=False
        )

        # Bar Chart
        results_text = ""
        for i, option in enumerate(self.options):
            count = vote_counts[i]
            percent = (count / total_votes * 100) if total_votes > 0 else 0
            
            bar_len = 10
            filled = int(percent / 10)
            bar = "█" * filled + "░" * (bar_len - filled)
            
            results_text += f"**{option}**\n{bar} {count} ({percent:.1f}%)\n\n"

        embed.add_field(name="📈 Hasil Sementara", value=results_text, inline=False)
        embed.set_footer(text=f"Total Suara: {total_votes}")

        # We need to fetch the message to edit it
        # Since we don't have the message object directly here easily without context,
        # we rely on the interaction that triggered this update usually.
        # But wait, `update_message` is called from button callback.
        # We can't easily edit the message from here without the interaction object 
        # OR storing the message object (which we can't persist).
        # SOLUTION: The button callback handles the interaction, but we want to update the message publicly.
        # We can't do `interaction.message.edit` because the interaction is ephemeral usually? 
        # No, button interactions allow editing the message.
        pass 
        # Actually, let's move the update logic to the button callback or a method that takes interaction.

    async def refresh_display(self, interaction: discord.Interaction):
        poll = self.manager.get_poll(self.message_id)
        if not poll:
            return

        vote_counts = [0] * len(self.options)
        total_votes = 0
        for vote_idx in poll["votes"].values():
            if 0 <= vote_idx < len(vote_counts):
                vote_counts[vote_idx] += 1
                total_votes += 1

        embed = interaction.message.embeds[0]
        # Update the results field (index 1 usually, but safer to find by name or rebuild)
        
        # Rebuild for safety
        new_embed = discord.Embed(
            title="📊 Polling Berlangsung",
            description=f"**{poll['question']}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        new_embed.add_field(name="⏱️ Berakhir", value=f"<t:{int(poll['end_time'])}:R>", inline=False)
        
        results_text = ""
        for i, option in enumerate(self.options):
            count = vote_counts[i]
            percent = (count / total_votes * 100) if total_votes > 0 else 0
            bar_len = 10
            filled = int(percent / 10)
            bar = "█" * filled + "░" * (bar_len - filled)
            results_text += f"**{option}**\n{bar} **{count}** ({percent:.1f}%)\n\n"
            
        new_embed.add_field(name="📈 Hasil Sementara", value=results_text, inline=False)
        # Use author_name if available, otherwise fallback to ID (but try to avoid raw mention in footer)
        author_text = poll.get('author_name', f"User {poll['author_id']}")
        new_embed.set_footer(text=f"Total Suara: {total_votes} • Poll by {author_text}")
        
        await interaction.message.edit(embed=new_embed)

# Override callback to use refresh_display
class PollButton(discord.ui.Button):
    def __init__(self, index: int, label: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label[:80], custom_id=f"poll_btn_{index}")
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: PollView = self.view
        if not view.manager.get_poll(view.message_id):
            await interaction.response.send_message("❌ Poll ini sudah berakhir.", ephemeral=True)
            return

        changed = view.manager.add_vote(view.message_id, interaction.user.id, self.index)
        if changed:
            await interaction.response.defer(ephemeral=True) # Acknowledge
            await view.refresh_display(interaction)
            await interaction.followup.send(f"✅ Kamu memilih: **{self.label}**", ephemeral=True)
        else:
            await interaction.response.send_message(f"ℹ️ Kamu sudah memilih **{self.label}**.", ephemeral=True)

class PollModal(discord.ui.Modal, title="Buat Polling Baru"):
    question = discord.ui.TextInput(label="Pertanyaan", placeholder="Apa warna kesukaanmu?", max_length=256)
    options = discord.ui.TextInput(label="Pilihan (Satu per baris)", placeholder="Merah\nBiru\nHijau", style=discord.TextStyle.paragraph)
    duration = discord.ui.TextInput(label="Durasi (Menit)", placeholder="60", default="60", min_length=1, max_length=4)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            duration_mins = int(self.duration.value)
            if duration_mins < 1: raise ValueError
        except:
            await interaction.response.send_message("❌ Durasi harus berupa angka (menit)!", ephemeral=True)
            return

        option_list = [opt.strip() for opt in self.options.value.split('\n') if opt.strip()]
        if len(option_list) < 2:
            await interaction.response.send_message("❌ Minimal 2 pilihan!", ephemeral=True)
            return
        if len(option_list) > 25:
            await interaction.response.send_message("❌ Maksimal 25 pilihan!", ephemeral=True)
            return

        # Create Embed
        embed = discord.Embed(
            title="📊 Polling Berlangsung",
            description=f"**{self.question.value}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        end_time = datetime.now() + timedelta(minutes=duration_mins)
        end_timestamp = end_time.timestamp()
        
        embed.add_field(name="⏱️ Berakhir", value=f"<t:{int(end_timestamp)}:R>", inline=False)
        
        # Initial Empty Results
        results_text = ""
        for opt in option_list:
            results_text += f"**{opt}**\n░░░░░░░░░░ **0** (0.0%)\n\n"
        embed.add_field(name="📈 Hasil Sementara", value=results_text, inline=False)
        embed.set_footer(text="Total Suara: 0")

        # Send Message
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        # Create View & Save
        self.cog.manager.create_poll(
            message.id, 
            interaction.channel_id, 
            interaction.guild_id, 
            self.question.value, 
            option_list, 
            end_timestamp,
            interaction.user.id,
            interaction.user.display_name
        )

        view = PollView(self.cog.manager, message.id, option_list)
        await message.edit(view=view)

# ==========================================
# MAIN COG
# ==========================================
class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.manager = PollManager()
        self.check_polls_task.start()

    def cog_unload(self):
        self.check_polls_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Poll Cog (Modern) is ready')
        # Re-register views for active polls to make them persistent
        for message_id, data in self.manager.polls.items():
            if data['active']:
                view = PollView(self.manager, int(message_id), data['options'])
                self.bot.add_view(view, message_id=int(message_id))

    @tasks.loop(seconds=60)
    async def check_polls_task(self):
        # Iterate copy of items to allow modification
        now = datetime.now().timestamp()
        expired_polls = []
        
        for message_id, data in self.manager.polls.items():
            if data['active'] and now >= data['end_time']:
                expired_polls.append(message_id)
        
        for mid in expired_polls:
            await self.end_poll(mid)

    async def end_poll(self, message_id: str):
        data = self.manager.get_poll(int(message_id))
        if not data: return

        channel = self.bot.get_channel(data['channel_id'])
        if channel:
            try:
                message = await channel.fetch_message(int(message_id))
                
                # Calculate Final Results
                vote_counts = [0] * len(data['options'])
                total_votes = 0
                for vote_idx in data["votes"].values():
                    if 0 <= vote_idx < len(vote_counts):
                        vote_counts[vote_idx] += 1
                        total_votes += 1
                
                # Determine Winner
                winner_idx = -1
                max_votes = -1
                if total_votes > 0:
                    max_votes = max(vote_counts)
                    # Check for tie
                    if vote_counts.count(max_votes) == 1:
                        winner_idx = vote_counts.index(max_votes)

                # Final Embed
                embed = discord.Embed(
                    title="🏁 Polling Selesai",
                    description=f"**{data['question']}**",
                    color=discord.Color.green() if total_votes > 0 else discord.Color.red(),
                    timestamp=datetime.now()
                )
                
                results_text = ""
                for i, option in enumerate(data['options']):
                    count = vote_counts[i]
                    percent = (count / total_votes * 100) if total_votes > 0 else 0
                    
                    medal = ""
                    if i == winner_idx: medal = "🏆 "
                    
                    bar_len = 10
                    filled = int(percent / 10)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    
                    results_text += f"{medal}**{option}**\n{bar} **{count}** ({percent:.1f}%)\n\n"

                embed.add_field(name="📊 Hasil Akhir", value=results_text, inline=False)
                author_text = data.get('author_name', f"User {data['author_id']}")
                embed.set_footer(text=f"Total Partisipan: {total_votes} • Poll by {author_text}")
                
                # Disable buttons
                view = PollView(self.manager, int(message_id), data['options'])
                for item in view.children:
                    item.disabled = True
                
                await message.edit(embed=embed, view=view)
                
                # Announce winner
                if winner_idx != -1:
                    await channel.send(f"🎉 Pemenang poll **{data['question']}** adalah: **{data['options'][winner_idx]}**!", reference=message)
                else:
                    await channel.send(f"🏁 Poll **{data['question']}** berakhir seri/tanpa suara.", reference=message)

            except discord.NotFound:
                print(f"⚠️ Message {message_id} not found, cannot update.")
            except Exception as e:
                print(f"❌ Error ending poll {message_id}: {e}")
        
        self.manager.end_poll(int(message_id))

    @app_commands.command(name="poll", description="Buat polling baru (Modern UI)")
    async def poll_command(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PollModal(self))

    @app_commands.command(name="poll-end", description="Akhiri polling secara manual")
    @app_commands.describe(message_id="ID Pesan Polling (Klik kanan -> Copy Message ID)")
    async def poll_end(self, interaction: discord.Interaction, message_id: str):
        try:
            mid = int(message_id)
            poll = self.manager.get_poll(mid)
            if not poll:
                await interaction.response.send_message("❌ Polling tidak ditemukan atau sudah berakhir.", ephemeral=True)
                return
            
            if poll['author_id'] != interaction.user.id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Kamu bukan pembuat poll ini!", ephemeral=True)
                return

            await interaction.response.send_message("✅ Mengakhiri polling...", ephemeral=True)
            await self.end_poll(str(mid))
            
        except ValueError:
            await interaction.response.send_message("❌ ID Pesan tidak valid.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Poll(bot))
