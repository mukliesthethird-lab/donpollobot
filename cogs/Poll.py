import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Union

class PollView(discord.ui.View):
    def __init__(self, poll_data: dict, timeout: int = None):
        super().__init__(timeout=timeout)
        self.poll_data = poll_data
        self.votes = {}  # {user_id: choice_index}
        self.is_ended = False
        
    @discord.ui.button(label='✅ Ya', style=discord.ButtonStyle.green, custom_id='poll_yes')
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote_interaction(interaction, 0, '✅')
    
    @discord.ui.button(label='❌ Tidak', style=discord.ButtonStyle.red, custom_id='poll_no')
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote_interaction(interaction, 1, '❌')
    
    async def handle_vote_interaction(self, interaction: discord.Interaction, choice: int, emoji: str):
        if self.is_ended:
            await interaction.response.send_message("❌ Poll ini sudah berakhir!", ephemeral=True)
            return
        await self.handle_vote(interaction, choice, emoji)
    
    @discord.ui.button(label='📊 Lihat Hasil', style=discord.ButtonStyle.secondary, custom_id='poll_results')
    async def view_results(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_results(interaction, final=False)
    
    @discord.ui.button(label='🛑 Akhiri Poll', style=discord.ButtonStyle.danger, custom_id='end_poll')
    async def end_poll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.poll_data['author_id']:
            await interaction.response.send_message(
                "❌ Hanya pembuat poll yang bisa mengakhiri polling ini!", 
                ephemeral=True
            )
            return
        
        if self.is_ended:
            await interaction.response.send_message("❌ Poll ini sudah berakhir!", ephemeral=True)
            return
        
        confirm_view = ConfirmEndPollView(self)
        embed = discord.Embed(
            title="⚠️ Konfirmasi Akhiri Poll",
            description="Apakah kamu yakin ingin mengakhiri polling ini sekarang?\n\n**Tindakan ini tidak bisa dibatalkan!**",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
    
    async def handle_vote(self, interaction: discord.Interaction, choice: int, emoji: str):
        user_id = interaction.user.id
        
        if user_id in self.votes:
            if self.votes[user_id] == choice:
                await interaction.response.send_message(
                    f"❌ Kamu sudah memilih {emoji}!", 
                    ephemeral=True
                )
                return
            else:
                self.votes[user_id] = choice
                await interaction.response.send_message(
                    f"✅ Pilihan berhasil diubah ke {emoji}!", 
                    ephemeral=True
                )
                return
        
        self.votes[user_id] = choice
        await interaction.response.send_message(
            f"✅ Terima kasih! Kamu memilih {emoji}", 
            ephemeral=True
        )
    
    async def show_results(self, interaction: discord.Interaction, final: bool = False):
        yes_votes = sum(1 for vote in self.votes.values() if vote == 0)
        no_votes = sum(1 for vote in self.votes.values() if vote == 1)
        total_votes = len(self.votes)
        
        yes_percent = (yes_votes / total_votes * 100) if total_votes > 0 else 0
        no_percent = (no_votes / total_votes * 100) if total_votes > 0 else 0
        
        bar_length = 10
        yes_bars = int(yes_percent / 10)
        no_bars = int(no_percent / 10)
        
        yes_bar = "█" * yes_bars + "░" * (bar_length - yes_bars)
        no_bar = "█" * no_bars + "░" * (bar_length - no_bars)
        
        title = "🏁 Hasil Akhir Poll" if final else "📊 Hasil Sementara Poll"
        embed = discord.Embed(
            title=title,
            description=f"**{self.poll_data['question']}**",
            color=discord.Color.blue() if not final else discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="✅ Ya",
            value=f"{yes_bar}\n**{yes_votes}** suara ({yes_percent:.1f}%)",
            inline=True
        )
        
        embed.add_field(
            name="❌ Tidak", 
            value=f"{no_bar}\n**{no_votes}** suara ({no_percent:.1f}%)",
            inline=True
        )
        
        embed.add_field(
            name="📈 Statistik",
            value=f"**Total Suara:** {total_votes}\n**Partisipasi:** {total_votes} orang",
            inline=False
        )
        
        if final and total_votes > 0:
            if yes_votes > no_votes:
                winner = "✅ **Ya** menang!"
                embed.color = discord.Color.green()
            elif no_votes > yes_votes:
                winner = "❌ **Tidak** menang!"
                embed.color = discord.Color.red()
            else:
                winner = "🤝 **Seri!**"
                embed.color = discord.Color.gold()
            
            embed.add_field(name="🏆 Pemenang", value=winner, inline=False)
        
        embed.set_footer(text=f"Poll by {self.poll_data['author']}")
        
        await interaction.response.send_message(embed=embed, ephemeral=not final)
    
    def end_poll_manually(self):
        """Method untuk mengakhiri poll secara manual"""
        self.is_ended = True
        for item in self.children:
            item.disabled = True

class ConfirmEndPollView(discord.ui.View):
    def __init__(self, poll_view):
        super().__init__(timeout=30)
        self.poll_view = poll_view
    
    @discord.ui.button(label='✅ Ya, Akhiri', style=discord.ButtonStyle.danger)
    async def confirm_end(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.poll_view.end_poll_manually()
        await self.poll_view.show_results(interaction, final=True)
        
        try:
            original_embed = discord.Embed(
                title="🏁 Poll Diakhiri oleh Pembuat",
                description=f"**{self.poll_view.poll_data['question']}**",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            original_embed.add_field(
                name="ℹ️ Informasi",
                value=f"Poll ini telah diakhiri secara manual oleh **{self.poll_view.poll_data['author']}**",
                inline=False
            )
            
            original_embed.set_author(name=self.poll_view.poll_data['author'])
            original_embed.set_footer(text="Poll berakhir lebih cepat dari jadwal")
            
            message = interaction.message
            if message:
                await message.edit(embed=original_embed, view=self.poll_view)
        except Exception as e:
            print(f"Error updating poll message: {e}")
        
        for item in self.children:
            item.disabled = True
        
        confirm_embed = discord.Embed(
            title="✅ Poll Berhasil Diakhiri",
            description="Polling telah diakhiri dan hasil akhir telah ditampilkan.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=confirm_embed, view=self)
    
    @discord.ui.button(label='❌ Batal', style=discord.ButtonStyle.secondary)
    async def cancel_end(self, interaction: discord.Interaction, button: discord.ui.Button):
        cancel_embed = discord.Embed(
            title="❌ Dibatalkan",
            description="Polling tetap berlanjut.",
            color=discord.Color.green()
        )
        
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=cancel_embed, view=self)

class MultiPollView(discord.ui.View):
    def __init__(self, poll_data: dict, timeout: int = None):
        super().__init__(timeout=timeout)
        self.poll_data = poll_data
        self.votes = {}  # {user_id: choice_index}
        self.is_ended = False
        
        # Buat button untuk setiap pilihan
        for i, choice in enumerate(poll_data['choices']):
            if i < 8:  # Maksimal 8 choice buttons + 2 action buttons = 10 (Discord limit)
                button = discord.ui.Button(
                    label=f"{i+1}. {choice[:20]}{'...' if len(choice) > 20 else ''}",
                    style=discord.ButtonStyle.primary,
                    custom_id=f'choice_{i}'
                )
                button.callback = self.create_choice_callback(i)
                self.add_item(button)
        
        # Tombol hasil
        results_button = discord.ui.Button(
            label='📊 Lihat Hasil',
            style=discord.ButtonStyle.secondary,
            custom_id='multi_results'
        )
        results_button.callback = self.show_results
        self.add_item(results_button)
        
        # Tombol akhiri poll (hanya untuk pembuat)
        end_button = discord.ui.Button(
            label='🛑 Akhiri Poll',
            style=discord.ButtonStyle.danger,
            custom_id='multi_end_poll'
        )
        end_button.callback = self.end_poll
        self.add_item(end_button)
    
    def create_choice_callback(self, choice_index: int):
        async def choice_callback(interaction: discord.Interaction):
            if self.is_ended:
                await interaction.response.send_message("❌ Poll ini sudah berakhir!", ephemeral=True)
                return
                
            user_id = interaction.user.id
            choice_text = self.poll_data['choices'][choice_index]
            
            if user_id in self.votes:
                if self.votes[user_id] == choice_index:
                    await interaction.response.send_message(
                        f"❌ Kamu sudah memilih **{choice_text}**!", 
                        ephemeral=True
                    )
                    return
                else:
                    self.votes[user_id] = choice_index
                    await interaction.response.send_message(
                        f"✅ Pilihan berhasil diubah ke **{choice_text}**!", 
                        ephemeral=True
                    )
                    return
            
            self.votes[user_id] = choice_index
            await interaction.response.send_message(
                f"✅ Terima kasih! Kamu memilih **{choice_text}**", 
                ephemeral=True
            )
        
        return choice_callback
    
    async def end_poll(self, interaction: discord.Interaction):
        if interaction.user.id != self.poll_data['author_id']:
            await interaction.response.send_message(
                "❌ Hanya pembuat poll yang bisa mengakhiri polling ini!", 
                ephemeral=True
            )
            return
        
        if self.is_ended:
            await interaction.response.send_message("❌ Poll ini sudah berakhir!", ephemeral=True)
            return
        
        confirm_view = ConfirmEndMultiPollView(self)
        embed = discord.Embed(
            title="⚠️ Konfirmasi Akhiri Poll Multi-Pilihan",
            description="Apakah kamu yakin ingin mengakhiri polling ini sekarang?\n\n**Tindakan ini tidak bisa dibatalkan!**",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
    
    async def show_results(self, interaction: discord.Interaction):
        results = {}
        for i, choice in enumerate(self.poll_data['choices']):
            results[choice] = sum(1 for vote in self.votes.values() if vote == i)
        
        total_votes = len(self.votes)
        
        embed = discord.Embed(
            title="📊 Hasil Poll Multi-Pilihan",
            description=f"**{self.poll_data['question']}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        
        results_text = ""
        for i, (choice, votes) in enumerate(sorted_results):
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            bar_length = int(percentage / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            medal = "🥇" if i == 0 and votes > 0 else "🥈" if i == 1 and votes > 0 else "🥉" if i == 2 and votes > 0 else "▫️"
            results_text += f"{medal} **{choice}**\n{bar}\n**{votes}** suara ({percentage:.1f}%)\n\n"
        
        embed.add_field(name="📈 Hasil", value=results_text or "Belum ada suara", inline=False)
        embed.add_field(name="📊 Total Suara", value=f"**{total_votes}** orang", inline=False)
        embed.set_footer(text=f"Poll by {self.poll_data['author']}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def end_poll_manually(self):
        self.is_ended = True
        for item in self.children:
            item.disabled = True

class ConfirmEndMultiPollView(discord.ui.View):
    def __init__(self, poll_view):
        super().__init__(timeout=30)
        self.poll_view = poll_view
    
    @discord.ui.button(label='✅ Ya, Akhiri', style=discord.ButtonStyle.danger)
    async def confirm_end(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.poll_view.end_poll_manually()
        await self.poll_view.show_results(interaction)
        
        for item in self.children:
            item.disabled = True
        
        confirm_embed = discord.Embed(
            title="✅ Poll Multi-Pilihan Berhasil Diakhiri",
            description="Polling telah diakhiri dan hasil akhir telah ditampilkan di atas.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=confirm_embed, view=self)
    
    @discord.ui.button(label='❌ Batal', style=discord.ButtonStyle.secondary)
    async def cancel_end(self, interaction: discord.Interaction, button: discord.ui.Button):
        cancel_embed = discord.Embed(
            title="❌ Dibatalkan",
            description="Polling multi-pilihan tetap berlanjut.",
            color=discord.Color.green()
        )
        
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=cancel_embed, view=self)

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_polls = {}  # {message_id: poll_data}

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Poll Cog is ready')

    async def validate_poll_input(self, interaction: discord.Interaction, question: str, time_limit: int, min_time: int = 1, max_time: int = 1440) -> bool:
        if not question.strip():
            await interaction.response.send_message("❌ Pertanyaan tidak boleh kosong!", ephemeral=True)
            return False
            
        if time_limit < min_time or time_limit > max_time:
            await interaction.response.send_message(f"❌ Batas waktu harus antara {min_time}-{max_time} menit!", ephemeral=True)
            return False
        
        return True

    @app_commands.command(name="poll", description="Buat polling sederhana dengan pilihan Ya/Tidak")
    @app_commands.describe(
        question="Pertanyaan yang ingin diajukan",
        time_limit="Batas waktu polling dalam menit (1-1440, default: 60)",
        anonymous="Apakah polling ini anonim? (default: False)"
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        time_limit: int = 60,
        anonymous: bool = False
    ):
        if not await self.validate_poll_input(interaction, question, time_limit):
            return

        poll_data = {
            'question': question,
            'author': interaction.user.display_name,
            'author_id': interaction.user.id,
            'anonymous': anonymous,
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(minutes=time_limit)
        }

        embed = discord.Embed(
            title="📊 Polling Dimulai!",
            description=f"**{question}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="⏱️ Informasi",
            value=f"**Durasi:** {time_limit} menit\n**Berakhir:** <t:{int(poll_data['end_time'].timestamp())}:R>\n**Anonim:** {'✅ Ya' if anonymous else '❌ Tidak'}",
            inline=False
        )
        
        embed.add_field(
            name="📋 Cara Vote",
            value="Klik tombol **✅ Ya** atau **❌ Tidak** di bawah untuk memberikan suara!",
            inline=False
        )
        
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="💡 Kamu bisa mengubah pilihan kapan saja selama polling berlangsung")

        view = PollView(poll_data, timeout=time_limit * 60)
        
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        
        self.active_polls[message.id] = {
            'data': poll_data,
            'view': view,
            'message': message,
            'interaction': interaction
        }

        asyncio.create_task(self.poll_timer(message.id, time_limit * 60))

    async def poll_timer(self, message_id: int, duration: int):
        await asyncio.sleep(duration)
        await self.end_poll_automatically(message_id)

    async def end_poll_automatically(self, message_id: int):
        if message_id not in self.active_polls:
            return
        
        poll_info = self.active_polls[message_id]
        view = poll_info['view']
        message = poll_info['message']
        interaction = poll_info['interaction']
        
        if view.is_ended:
            return

        try:
            yes_votes = sum(1 for vote in view.votes.values() if vote == 0)
            no_votes = sum(1 for vote in view.votes.values() if vote == 1)
            total_votes = len(view.votes)
            
            view.end_poll_manually()
            
            final_embed = discord.Embed(
                title="🏁 Polling Selesai!",
                description=f"**{view.poll_data['question']}**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            if total_votes > 0:
                yes_percent = (yes_votes / total_votes * 100)
                no_percent = (no_votes / total_votes * 100)
                
                bar_length = 10
                yes_bars = int(yes_percent / 10)
                no_bars = int(no_percent / 10)
                
                yes_bar = "█" * yes_bars + "░" * (bar_length - yes_bars)
                no_bar = "█" * no_bars + "░" * (bar_length - no_bars)
                
                final_embed.add_field(
                    name="✅ Ya",
                    value=f"{yes_bar}\n**{yes_votes}** suara ({yes_percent:.1f}%)",
                    inline=True
                )
                
                final_embed.add_field(
                    name="❌ Tidak", 
                    value=f"{no_bar}\n**{no_votes}** suara ({no_percent:.1f}%)",
                    inline=True
                )
                
                if yes_votes > no_votes:
                    winner = "✅ **Ya** menang!"
                    final_embed.color = discord.Color.green()
                elif no_votes > yes_votes:
                    winner = "❌ **Tidak** menang!"
                    final_embed.color = discord.Color.red()
                else:
                    winner = "🤝 **Seri!**"
                    final_embed.color = discord.Color.gold()
                
                final_embed.add_field(name="🏆 Pemenang", value=winner, inline=False)
            else:
                final_embed.add_field(name="📊 Hasil", value="Tidak ada suara yang masuk", inline=False)
            
            final_embed.add_field(name="📈 Total Suara", value=f"**{total_votes}** orang", inline=False)
            final_embed.set_author(name=view.poll_data['author'])
            final_embed.set_footer(text="Poll berakhir secara otomatis")
            
            await message.edit(embed=final_embed, view=view)
            
            result_embed = discord.Embed(
                title="📊 Hasil Final Polling",
                description=f"**{view.poll_data['question']}**\n\n*Poll telah berakhir secara otomatis*",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            if total_votes > 0:
                result_embed.add_field(
                    name="📊 Hasil Lengkap",
                    value=f"✅ **Ya:** {yes_votes} suara ({yes_percent:.1f}%)\n❌ **Tidak:** {no_votes} suara ({no_percent:.1f}%)",
                    inline=False
                )
                result_embed.add_field(name="🏆 Pemenang", value=winner, inline=False)
            else:
                result_embed.add_field(name="📊 Hasil", value="Tidak ada suara yang masuk", inline=False)
            
            result_embed.set_footer(text=f"Poll by {view.poll_data['author']}")
            
            await interaction.followup.send(embed=result_embed)
            
        except Exception as e:
            print(f"Error ending poll automatically: {e}")
        finally:
            if message_id in self.active_polls:
                del self.active_polls[message_id]

    @app_commands.command(name="poll-multi", description="Buat polling dengan banyak pilihan")
    @app_commands.describe(
        question="Pertanyaan yang ingin diajukan",
        choices="Pilihan yang tersedia (pisahkan dengan koma, max 10)",
        time_limit="Batas waktu polling dalam menit (1-1440, default: 60)"
    )
    async def poll_multi(
        self,
        interaction: discord.Interaction,
        question: str,
        choices: str,
        time_limit: int = 60
    ):
        if not await self.validate_poll_input(interaction, question, time_limit):
            return

        choice_list = [choice.strip() for choice in choices.split(',')]
        choice_list = [choice for choice in choice_list if choice]
        
        if len(choice_list) < 2:
            await interaction.response.send_message("❌ Minimal harus ada 2 pilihan!", ephemeral=True)
            return
            
        if len(choice_list) > 10:
            await interaction.response.send_message("❌ Maksimal 10 pilihan!", ephemeral=True)
            return

        poll_data = {
            'question': question,
            'choices': choice_list,
            'author': interaction.user.display_name,
            'author_id': interaction.user.id,
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(minutes=time_limit)
        }

        embed = discord.Embed(
            title="📊 Polling Multi-Pilihan Dimulai!",
            description=f"**{question}**",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        choices_text = "\n".join([f"{i+1}. {choice}" for i, choice in enumerate(choice_list)])
        embed.add_field(name="📋 Pilihan Tersedia", value=choices_text, inline=False)
        
        embed.add_field(
            name="⏱️ Informasi",
            value=f"**Durasi:** {time_limit} menit\n**Berakhir:** <t:{int(poll_data['end_time'].timestamp())}:R>",
            inline=False
        )
        
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="💡 Klik salah satu tombol di bawah untuk memberikan suara!")

        view = MultiPollView(poll_data, timeout=time_limit * 60)
        
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        
        self.active_polls[message.id] = {
            'data': poll_data,
            'view': view,
            'message': message,
            'interaction': interaction
        }

        asyncio.create_task(self.multi_poll_timer(message.id, time_limit * 60))

    async def multi_poll_timer(self, message_id: int, duration: int):
        await asyncio.sleep(duration)
        await self.end_multi_poll_automatically(message_id)

    async def end_multi_poll_automatically(self, message_id: int):
        if message_id not in self.active_polls:
            return
        
        poll_info = self.active_polls[message_id]
        view = poll_info['view']
        message = poll_info['message']
        interaction = poll_info['interaction']
        
        if view.is_ended:
            return

        try:
            view.end_poll_manually()
            
            final_embed = discord.Embed(
                title="🏁 Polling Multi-Pilihan Selesai!",
                description=f"**{view.poll_data['question']}**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            choices_text = "\n".join([f"{i+1}. {choice}" for i, choice in enumerate(view.poll_data['choices'])])
            final_embed.add_field(name="📋 Pilihan", value=choices_text, inline=False)
            
            final_embed.set_author(name=view.poll_data['author'])
            final_embed.set_footer(text="Poll berakhir secara otomatis")
            
            await message.edit(embed=final_embed, view=view)
            
            results = {}
            for i, choice in enumerate(view.poll_data['choices']):
                results[choice] = sum(1 for vote in view.votes.values() if vote == i)
            
            total_votes = len(view.votes)
            
            result_embed = discord.Embed(
                title="📊 Hasil Final Multi-Poll",
                description=f"**{view.poll_data['question']}**\n\n*Poll telah berakhir secara otomatis*",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            if total_votes > 0:
                sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
                
                results_text = ""
                for i, (choice, votes) in enumerate(sorted_results):
                    percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                    bar_length = int(percentage / 5)
                    bar = "█" * bar_length + "░" * (20 - bar_length)
                    
                    medal = "🥇" if i == 0 and votes > 0 else "🥈" if i == 1 and votes > 0 else "🥉" if i == 2 and votes > 0 else "▫️"
                    results_text += f"{medal} **{choice}**\n{bar}\n**{votes}** suara ({percentage:.1f}%)\n\n"
                
                result_embed.add_field(name="📈 Hasil Lengkap", value=results_text, inline=False)
                result_embed.add_field(name="🏆 Pemenang", value=f"**{sorted_results[0][0]}** dengan **{sorted_results[0][1]}** suara!", inline=False)
            else:
                result_embed.add_field(name="📊 Hasil", value="Tidak ada suara yang masuk", inline=False)
            
            result_embed.add_field(name="📊 Total Suara", value=f"**{total_votes}** orang", inline=False)
            result_embed.set_footer(text=f"Poll by {view.poll_data['author']}")
            
            await interaction.followup.send(embed=result_embed)
            
        except Exception as e:
            print(f"Error ending multi-poll automatically: {e}")
        finally:
            if message_id in self.active_polls:
                del self.active_polls[message_id]

    @app_commands.command(name="poll-quick", description="Buat polling cepat dengan reaksi emoji")
    @app_commands.describe(
        question="Pertanyaan yang ingin diajukan",
        time_limit="Batas waktu polling dalam menit (1-60, default: 10)"
    )
    async def poll_quick(
        self,
        interaction: discord.Interaction,
        question: str,
        time_limit: int = 10
    ):
        if not await self.validate_poll_input(interaction, question, time_limit, 1, 60):
            return

        embed = discord.Embed(
            title="⚡ Polling Cepat",
            description=f"**{question}**",
            color=discord.Color.yellow(),
            timestamp=datetime.now()
        )
        
        end_time = datetime.now() + timedelta(minutes=time_limit)
        embed.add_field(
            name="⏱️ Info",
            value=f"**Durasi:** {time_limit} menit\n**Berakhir:** <t:{int(end_time.timestamp())}:R>\n\n**Cara vote:** Klik reaksi ✅ atau ❌",
            inline=False
        )
        
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="💡 Polling cepat menggunakan sistem reaksi")

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        try:
            await message.add_reaction("✅")
            await message.add_reaction("❌")
        except Exception as e:
            await interaction.followup.send("❌ Gagal menambahkan reaksi ke polling!")
            return

        await asyncio.sleep(time_limit * 60)

        try:
            message = await interaction.channel.fetch_message(message.id)
            
            yes_count = 0
            no_count = 0
            
            for reaction in message.reactions:
                if reaction.emoji == "✅":
                    yes_count = reaction.count - 1
                elif reaction.emoji == "❌":
                    no_count = reaction.count - 1
            
            total_votes = yes_count + no_count
            
            embed_result = discord.Embed(
                title="🏁 Hasil Polling Cepat",
                description=f"**{question}**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            if total_votes > 0:
                yes_percent = (yes_count / total_votes * 100)
                no_percent = (no_count / total_votes * 100)
                
                embed_result.add_field(
                    name="📊 Hasil",
                    value=f"✅ **Ya:** {yes_count} suara ({yes_percent:.1f}%)\n❌ **Tidak:** {no_count} suara ({no_percent:.1f}%)",
                    inline=False
                )
                
                if yes_count > no_count:
                    winner = "✅ **Ya** menang!"
                elif no_count > yes_count:
                    winner = "❌ **Tidak** menang!"
                else:
                    winner = "🤝 **Seri!**"
                
                embed_result.add_field(name="🏆 Pemenang", value=winner, inline=False)
            else:
                embed_result.add_field(name="📊 Hasil", value="Tidak ada suara yang masuk", inline=False)
            
            embed_result.add_field(name="📈 Total Suara", value=f"**{total_votes}** suara", inline=False)
            embed_result.set_footer(text=f"Poll by {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed_result)
            
        except discord.NotFound:
            await interaction.followup.send("❌ Pesan polling tidak ditemukan!")
        except Exception as e:
            await interaction.followup.send("❌ Gagal mendapatkan hasil polling!")

async def setup(bot):
    await bot.add_cog(Poll(bot))
# Maintenance update
