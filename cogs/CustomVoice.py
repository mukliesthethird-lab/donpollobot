import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput, Select
import asyncio

class VoiceCustom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_voice = {}  # {channel_id: {'owner_id': int, 'control_message_id': int}}
        self.processing_users = set() # Set to track users currently creating a channel
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Custom Voice Cog is ready")

    @app_commands.command(name="setup_voice", description="Siapkan sistem voice channel otomatis")
    @app_commands.default_permissions(manage_channels=True)
    async def setup_voice(self, interaction: discord.Interaction):
        """Set up automatic voice channel system"""
        guild = interaction.guild

        # Check if category exists
        category = discord.utils.get(guild.categories, name="Ruang Voice")
        if category:
            # Delete old category if exists
            for channel in category.channels:
                await channel.delete()
            await category.delete()

        # Create new category
        category = await guild.create_category("Ruang Voice")

        # Create trigger voice channel
        channel = await guild.create_voice_channel(
            "➕ Buat Voice", 
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(
                    connect=True,
                    speak=False,
                    send_messages=False
                )
            }
        )
        
        embed = discord.Embed(
            title="✅ Setup Berhasil",
            description=f"Sistem voice custom telah disiapkan di {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # JOIN ➕ Buat Voice
        if after.channel and after.channel.name == "➕ Buat Voice":
            # Check if user is already being processed
            if member.id in self.processing_users:
                return
            
            self.processing_users.add(member.id)
            
            try:
                guild = member.guild
                category = after.channel.category

                # Create custom voice channel with full permissions for owner
                new_channel = await guild.create_voice_channel(
                    f"🔊 Ruang {member.display_name}",
                    category=category,
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(
                            connect=True,
                            view_channel=True,
                            send_messages=True
                        ),
                        member: discord.PermissionOverwrite(
                            manage_channels=True,
                            move_members=True,
                            mute_members=True,
                            deafen_members=True,
                            priority_speaker=True
                        )
                    }
                )

                self.channel_voice[new_channel.id] = {
                    'owner_id': member.id,
                    'control_message_id': None
                }
                await member.move_to(new_channel)
                await self.send_panel(member, new_channel)
                
            except Exception as e:
                print(f"Error creating voice channel: {e}")
            finally:
                # Remove user from processing set after a short delay to ensure move is complete
                await asyncio.sleep(1) 
                self.processing_users.discard(member.id)

        # LEAVE or MOVE from custom channel
        if before.channel and before.channel.id in self.channel_voice:
            channel_data = self.channel_voice[before.channel.id]
            
            # Delete if empty
            if len(before.channel.members) == 0:
                # Delete control panel if exists
                if channel_data.get('control_message_id'):
                    try:
                        channel = before.channel
                        message = await channel.fetch_message(channel_data['control_message_id'])
                        await message.delete()
                    except:
                        pass
                
                await before.channel.delete()
                del self.channel_voice[before.channel.id]

    async def send_panel(self, member: discord.Member, channel: discord.VoiceChannel):
        """Send control panel to voice channel"""
        try:
        
            # Control panel
            embed = discord.Embed(
                title="🎛️ Controller Voice Room",
                description=f"Panel kontrol untuk ruang voice {member.display_name}",
                color=discord.Color.blurple()
            )
            
            # Get current permissions
            default_perms = channel.overwrites_for(channel.guild.default_role)
            lock_status = "🔒 Terkunci" if default_perms.connect is False else "🔓 Terbuka"
            visibility_status = "🙈 Tersembunyi" if default_perms.view_channel is False else "👁️ Terlihat"
            
            embed.add_field(name="Channel", value=channel.mention, inline=True)
            embed.add_field(name="Pemilik", value=member.mention, inline=True)
            embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
            embed.add_field(name="Anggota", value=f"{len(channel.members)}/{channel.user_limit or '∞'}", inline=True)
            embed.add_field(name="Bitrate", value=f"{channel.bitrate//1000}kbps", inline=True)
            embed.add_field(name="Region", value=channel.rtc_region or "Otomatis", inline=True)
            embed.add_field(name="Status", value=lock_status, inline=True)
            embed.add_field(name="Visibilitas", value=visibility_status, inline=True)
            
            view = PanelVoiceView(self.bot, channel, member)
            message = await channel.send(embed=embed, view=view)
            
            # Save message ID
            self.channel_voice[channel.id]['control_message_id'] = message.id
            
        except Exception as e:
            print(f"Failed to send control panel: {e}")


class PanelVoiceView(View):
    def __init__(self, bot, voice_channel, owner):
        super().__init__(timeout=None)
        self.bot = bot
        self.voice_channel = voice_channel
        self.owner = owner

        # Add dropdown menus
        self.add_item(MainControlMenu())
        self.add_item(RegionMenu())
        self.add_item(UserManagementMenu())

    async def interaction_check(self, interaction: discord.Interaction):
        """Check if user is room owner"""
        cog = self.bot.get_cog("VoiceCustom")
        if not cog:
            return False
            
        channel_data = cog.channel_voice.get(self.voice_channel.id)
        if not channel_data:
            return False
            
        if interaction.user.id != channel_data['owner_id']:
            await interaction.response.send_message("❌ Anda harus menjadi pemilik ruangan untuk menggunakan ini.", ephemeral=True)
            return False
            
        return True


class MainControlMenu(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Change Name", value="rename", description="Ubah nama ruangan", emoji="🔤"),
            discord.SelectOption(label="Bitrate", value="bitrate", description="Atur kualitas audio (8-384kbps)", emoji="🎚️"),
            discord.SelectOption(label="User Limit", value="limit", description="Atur jumlah maksimal user", emoji="👥"),
            discord.SelectOption(label="Lock/Unlock", value="lock", description="Toggle akses ruangan", emoji="🔒"),
            discord.SelectOption(label="Visibility", value="visibility", description="Toggle visibilitas ruangan", emoji="👁️"),
            discord.SelectOption(label="Transfer Ownership", value="transfer", description="Transfer kepemilikan", emoji="👑"),
            discord.SelectOption(label="Delete", value="delete", description="Hapus ruangan ini", emoji="🗑️")
        ]
        super().__init__(placeholder="🎛️ Kontrol Utama", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        
        if choice == "rename":
            await self.handle_rename(interaction)
        elif choice == "bitrate":
            await self.handle_bitrate(interaction)
        elif choice == "limit":
            await self.handle_limit(interaction)
        elif choice == "lock":
            await self.handle_lock(interaction)
        elif choice == "visibility":
            await self.handle_visibility(interaction)
        elif choice == "transfer":
            await self.handle_transfer(interaction)
        elif choice == "delete":
            await self.handle_delete(interaction)

    async def handle_rename(self, interaction: discord.Interaction):
        modal = Modal(title="Ganti Nama Ruangan")
        modal.add_item(TextInput(label="Nama Baru", placeholder="Masukkan nama baru untuk ruangan", max_length=100))
        
        async def on_submit(modal_interaction: discord.Interaction):
            new_name = modal.children[0].value
            try:
                await interaction.channel.edit(name=new_name)
                await modal_interaction.response.send_message(f"✅ Nama ruangan diubah menjadi: {new_name}", ephemeral=True)
                await update_control_panel(self.view.bot, interaction.channel.id)
            except Exception as e:
                await modal_interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    async def handle_bitrate(self, interaction: discord.Interaction):
        modal = Modal(title="Atur Bitrate")
        modal.add_item(TextInput(label="Bitrate (8-384)", placeholder="Masukkan bitrate dalam kbps"))
        
        async def on_submit(modal_interaction: discord.Interaction):
            try:
                bitrate = int(modal.children[0].value)
                if not 8 <= bitrate <= 384:
                    raise ValueError("Bitrate harus antara 8-384")
                    
                await interaction.channel.edit(bitrate=bitrate*1000)
                await modal_interaction.response.send_message(f"✅ Bitrate diatur ke {bitrate}kbps", ephemeral=True)
                await update_control_panel(self.view.bot, interaction.channel.id)
            except Exception as e:
                await modal_interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    async def handle_limit(self, interaction: discord.Interaction):
        modal = Modal(title="Atur Batas User")
        modal.add_item(TextInput(label="Max User (0=tidak terbatas)", placeholder="Masukkan jumlah maksimal user"))
        
        async def on_submit(modal_interaction: discord.Interaction):
            try:
                limit = int(modal.children[0].value)
                if limit < 0:
                    raise ValueError("Batas harus 0 atau lebih tinggi")
                    
                await interaction.channel.edit(user_limit=limit if limit > 0 else None)
                await modal_interaction.response.send_message(
                    f"✅ Batas user diatur ke {limit if limit > 0 else 'tidak terbatas'}", 
                    ephemeral=True
                )
                await update_control_panel(self.view.bot, interaction.channel.id)
            except Exception as e:
                await modal_interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    async def handle_lock(self, interaction: discord.Interaction):
        current = interaction.channel.overwrites_for(interaction.guild.default_role).connect
        new_value = False if current else True
        
        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            connect=new_value
        )
        
        await interaction.response.send_message(
            f"✅ Ruangan {'dikunci' if not new_value else 'dibuka'}!", 
            ephemeral=True
        )
        await update_control_panel(self.view.bot, interaction.channel.id)

    async def handle_visibility(self, interaction: discord.Interaction):
        current = interaction.channel.overwrites_for(interaction.guild.default_role).view_channel
        new_value = False if current else True
        
        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            view_channel=new_value
        )
        
        await interaction.response.send_message(
            f"✅ Ruangan {'disembunyikan' if not new_value else 'ditampilkan'}!", 
            ephemeral=True
        )
        await update_control_panel(self.view.bot, interaction.channel.id)

    async def handle_transfer(self, interaction: discord.Interaction):
        modal = Modal(title="Transfer Kepemilikan")
        modal.add_item(TextInput(label="ID User atau @mention", placeholder="Masukkan ID atau @mention pemilik baru"))
        
        async def on_submit(modal_interaction: discord.Interaction):
            try:
                user_input = modal.children[0].value
                user = None
                
                # Try to get by ID
                try:
                    user = interaction.guild.get_member(int(user_input))
                except ValueError:
                    # Try to get by mention
                    if user_input.startswith("<@") and user_input.endswith(">"):
                        user_id = user_input[2:-1]
                        if user_id.startswith("!"):
                            user_id = user_id[1:]
                        user = interaction.guild.get_member(int(user_id))
                
                if not user:
                    await modal_interaction.response.send_message("❌ User tidak ditemukan", ephemeral=True)
                    return
                
                # Update permissions
                await interaction.channel.set_permissions(
                    user,
                    manage_channels=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True
                )
                
                # Update owner in database
                cog = self.view.bot.get_cog("VoiceCustom")
                if cog and interaction.channel.id in cog.channel_voice:
                    cog.channel_voice[interaction.channel.id]['owner_id'] = user.id
                
                await modal_interaction.response.send_message(
                    f"✅ Kepemilikan ditransfer ke {user.mention}!",
                    ephemeral=True
                )
                await update_control_panel(self.view.bot, interaction.channel.id)
                
            except Exception as e:
                await modal_interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    async def handle_delete(self, interaction: discord.Interaction):
        cog = self.view.bot.get_cog("VoiceCustom")
        if cog and interaction.channel.id in cog.channel_voice:
            del cog.channel_voice[interaction.channel.id]
            
        await interaction.channel.delete()
        await interaction.response.send_message("✅ Ruangan dihapus!", ephemeral=True)


class RegionMenu(Select):
    def __init__(self):
        regions = [
            ("Otomatis", None),
            ("US Barat", "us-west"),
            ("US Timur", "us-east"),
            ("US Tengah", "us-central"),
            ("Eropa", "europe"),
            ("London", "london"),
            ("Amsterdam", "amsterdam"),
            ("Singapura", "singapore"),
            ("Sydney", "sydney"),
            ("Jepang", "japan"),
            ("Brasil", "brazil")
        ]
        
        options = [
            discord.SelectOption(label=name, value=value or "auto", description=f"Atur region ke {name or 'otomatis'}")
            for name, value in regions
        ]
        super().__init__(placeholder="🌍 Region Voice", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        region = self.values[0] if self.values[0] != "auto" else None
        await interaction.channel.edit(rtc_region=region)
        
        region_name = next((name for name, value in [
            ("Otomatis", None),
            ("US Barat", "us-west"),
            ("US Timur", "us-east"),
            ("US Tengah", "us-central"),
            ("Eropa", "europe"),
            ("London", "london"),
            ("Amsterdam", "amsterdam"),
            ("Singapura", "singapore"),
            ("Sydney", "sydney"),
            ("Jepang", "japan"),
            ("Brasil", "brazil")
        ] if value == region), "Otomatis")
        
        await interaction.response.send_message(
            f"✅ Region voice diatur ke {region_name}!",
            ephemeral=True
        )
        await update_control_panel(self.view.bot, interaction.channel.id)


class UserManagementMenu(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Undang User", value="invite", description="Izinkan user bergabung", emoji="📨"),
            discord.SelectOption(label="Kick User", value="kick", description="Keluarkan user dari ruangan", emoji="👢"),
            discord.SelectOption(label="Blokir User", value="block", description="Blokir user bergabung", emoji="🚫")
        ]
        super().__init__(placeholder="👥 Manajemen User", options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        
        if choice == "invite":
            await self.handle_invite(interaction)
        elif choice == "kick":
            await self.handle_kick(interaction)
        elif choice == "block":
            await self.handle_block(interaction)

    async def handle_invite(self, interaction: discord.Interaction):
        modal = Modal(title="Undang User")
        modal.add_item(TextInput(label="ID User atau @mention", placeholder="Masukkan user yang ingin diundang"))
        
        async def on_submit(modal_interaction: discord.Interaction):
            try:
                user_input = modal.children[0].value
                user = None
                
                # Try to get by ID
                try:
                    user = interaction.guild.get_member(int(user_input))
                except ValueError:
                    # Try to get by mention
                    if user_input.startswith("<@") and user_input.endswith(">"):
                        user_id = user_input[2:-1]
                        if user_id.startswith("!"):
                            user_id = user_id[1:]
                        user = interaction.guild.get_member(int(user_id))
                
                if not user:
                    await modal_interaction.response.send_message("❌ User tidak ditemukan", ephemeral=True)
                    return
                
                await interaction.channel.set_permissions(
                    user,
                    connect=True,
                    view_channel=True
                )
                
                await modal_interaction.response.send_message(
                    f"✅ {user.mention} sekarang dapat bergabung ke ruangan!",
                    ephemeral=True
                )
                
            except Exception as e:
                await modal_interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    async def handle_kick(self, interaction: discord.Interaction):
        if len(interaction.channel.members) <= 1:
            await interaction.response.send_message("❌ Tidak ada user lain di ruangan", ephemeral=True)
            return
            
        options = [
            discord.SelectOption(
                label=member.display_name,
                value=str(member.id),
                description=f"Kick {member.name}"
            )
            for member in interaction.channel.members
            if member.id != interaction.user.id
        ][:25]  # Discord limit
        
        if not options:
            await interaction.response.send_message("❌ Tidak ada user lain di ruangan", ephemeral=True)
            return
            
        view = View()
        select = Select(placeholder="Pilih user untuk dikick", options=options)
        
        async def callback(select_interaction: discord.Interaction):
            user_id = int(select.values[0])
            member = interaction.guild.get_member(user_id)
            if member and member.voice and member.voice.channel == interaction.channel:
                await member.move_to(None)
                await select_interaction.response.send_message(
                    f"👢 {member.display_name} telah dikeluarkan!",
                    ephemeral=True
                )
            else:
                await select_interaction.response.send_message("❌ User tidak ditemukan", ephemeral=True)
                
        select.callback = callback
        view.add_item(select)
        await interaction.response.send_message("Pilih user untuk dikick:", view=view, ephemeral=True)

    async def handle_block(self, interaction: discord.Interaction):
        modal = Modal(title="Blokir User")
        modal.add_item(TextInput(label="ID User atau @mention", placeholder="Masukkan user yang ingin diblokir"))
        
        async def on_submit(modal_interaction: discord.Interaction):
            try:
                user_input = modal.children[0].value
                user = None
                
                # Try to get by ID
                try:
                    user = interaction.guild.get_member(int(user_input))
                except ValueError:
                    # Try to get by mention
                    if user_input.startswith("<@") and user_input.endswith(">"):
                        user_id = user_input[2:-1]
                        if user_id.startswith("!"):
                            user_id = user_id[1:]
                        user = interaction.guild.get_member(int(user_id))
                
                if not user:
                    await modal_interaction.response.send_message("❌ User tidak ditemukan", ephemeral=True)
                    return
                
                await interaction.channel.set_permissions(
                    user,
                    connect=False,
                    view_channel=False
                )
                
                # Kick if currently in channel
                if user.voice and user.voice.channel == interaction.channel:
                    await user.move_to(None)
                
                await modal_interaction.response.send_message(
                    f"🚫 {user.mention} telah diblokir dari ruangan!",
                    ephemeral=True
                )
                
            except Exception as e:
                await modal_interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)


async def update_control_panel(bot, channel_id):
    """Update control panel embed"""
    try:
        cog = bot.get_cog("VoiceCustom")
        if not cog or channel_id not in cog.channel_voice:
            return
            
        channel = bot.get_channel(channel_id)
        if not channel:
            return
            
        channel_data = cog.channel_voice[channel_id]
        message_id = channel_data.get('control_message_id')
        if not message_id:
            return
            
        try:
            message = await channel.fetch_message(message_id)
        except:
            return
            
        owner = channel.guild.get_member(channel_data['owner_id'])
        if not owner:
            return
            
        # Get current permissions
        default_perms = channel.overwrites_for(channel.guild.default_role)
        lock_status = "🔒 Terkunci" if default_perms.connect is False else "🔓 Terbuka"
        visibility_status = "🙈 Tersembunyi" if default_perms.view_channel is False else "👁️ Terlihat"
        
        # Update embed
        embed = message.embeds[0]
        embed.clear_fields()
        
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Pemilik", value=owner.mention, inline=True)
        embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
        embed.add_field(name="Anggota", value=f"{len(channel.members)}/{channel.user_limit or '∞'}", inline=True)
        embed.add_field(name="Bitrate", value=f"{channel.bitrate//1000}kbps", inline=True)
        embed.add_field(name="Region", value=channel.rtc_region or "Otomatis", inline=True)
        embed.add_field(name="Status", value=lock_status, inline=True)
        embed.add_field(name="Visibilitas", value=visibility_status, inline=True)
        embed.add_field(name="Info", value="Gunakan menu dropdown di bawah untuk mengatur ruang Anda", inline=False)
        
        view = PanelVoiceView(cog.bot, channel, owner)
        await message.edit(embed=embed, view=view)
        
    except Exception as e:
        print(f"Error updating control panel: {e}")


async def setup(bot):
    await bot.add_cog(VoiceCustom(bot))
