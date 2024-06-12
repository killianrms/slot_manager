import os
import time
from discord_slash import SlashCommand, SlashContext
import discord
from discord.ext import commands, tasks
import sqlite3
import asyncio
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
from discord_slash.utils.manage_commands import create_option, create_choice
from pytz import timezone
import schedule
from discord import Intents
from pymongo import MongoClient

load_dotenv()  # take environment variables .env.
TOKEN = os.getenv('DISCORD_TOKEN')

# Create a connection to the SQLite database
conn = sqlite3.connect('slots.db')
c = conn.cursor()

# Database connection
client = MongoClient('mongodb+srv://revilojust:Kapitanoliver3007.@cluster0.lnjkm4l.mongodb.net/')
db = client['LicenceManager']
users = db['users']

intents = Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)
slash = SlashCommand(bot, sync_commands=True)  # Declares slash commands through the bot.
@bot.event
async def on_guild_join(guild):
    with open('setup.json', 'r') as f:
        if f.read().strip():
            f.seek(0)  # reset file position to the beginning
            data = json.load(f)
        else:
            data = {}

    guild_id = str(guild.id)
    if guild_id in data:
        staff_role_id = data[guild_id]['Staff_Role']
        rules = data[guild_id]['rules']

total_users = sum(guild.member_count for guild in bot.guilds)

if os.stat("setup.json").st_size != 0:  
    with open("setup.json", "r") as f:  
        data = json.load(f)
else:
    print("File is empty.")

@bot.event
async def on_ready():
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    # Print the ASCII art
    print(r"""
      ____  _                 ____        _   
     / ___|| |__   ___  _ __ | __ )  ___ | |_ 
     \___ \| '_ \ / _ \| '_ \|  _ \ / _ \| __|
      ___) | | | | (_) | |_) | |_) | (_) | |_ 
     |____/|_| |_|\___/| .__/|____/ \___/ \__|
                       |_|                    
    """)
    print("By Kozyq")

    # Set the bot's activity and status
    await bot.change_presence(activity = discord.Activity(type=discord.ActivityType.watching, name=".gg/dealabs"))
    bot.loop.create_task(schedule_clear_pings())
    await check_slots()
    print("Started Checking Slots.")

    # Start a new thread that runs the scheduler
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)
    

    # Load end times from the database
    c.execute("SELECT channel_id, end_time FROM slots")
    slots = c.fetchall()
async def clear_pings():
    with open('pings.json', 'w') as f:
        json.dump({}, f)

    with open('setup.json', 'r') as f:
        data = json.load(f)

    for guild_id, guild_data in data.items():
        if 'Reset_Pings_Channel' in guild_data:
            channel_id = guild_data['Reset_Pings_Channel']
        else:
            print(f"'Reset_Pings_Channel' not found in setup.json for guild {guild_id}")
            continue
        if 'Slot_Owner_Role' in guild_data:
            owner_id = guild_data['Slot_Owner_Role']
        else:
            print(f"'Slot_Owner_Role' not found in setup.json for guild {guild_id}")
            continue

        guild = bot.get_guild(int(guild_id))
        if guild is None:
            print(f"Guild with ID {guild_id} not found.")
            continue
        channel = guild.get_channel(int(channel_id))
        owner = guild.get_role(int(owner_id))

        await channel.send(f'`🔕`{owner.mention}, Pings have been reset.')

async def schedule_clear_pings():
    schedule.every().day.at("00:00").do(lambda: bot.loop.create_task(clear_pings()))
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

TIME_UNITS = {"s": 1, "d": 86400, "w": 604800, "m": 2629743, "l": 3155695200}
bot.load_extension('cogs.setup')
bot.load_extension("cogs.redeem")
# Check if slots.json exists and is not empty, if not, create and initialize it
if not os.path.exists('slots.json') or os.path.getsize('slots.json') == 0:
    with open('slots.json', 'w') as f:
        json.dump({}, f)
@slash.slash(name="slot", description="Creates a slot", options=[
    {
        "name": "user",
        "description": "ID of the user",
        "type": 6,  # Type 6 is for discord.User
        "required": True
    },
    {
        "name": "name",
        "description": "Name of the slot",
        "type": 3,
        "required": True
    },
    {
        "name": "category",
        "description": "Category where the channel will be created",
        "type": 7,  # Type 7 is for discord.CategoryChannel
        "required": True
    },
    {
        "name": "duration",
        "description": "Duration (s = Seconds, d = Days, w = Weeks, m = Months, l = Lifetime)",
        "type": 3,  # Type 3 is for string
        "required": True
    },
    {
        "name": "everyone_limit",
        "description": "Limit for everyone pings",
        "type": 4,
        "required": True
    },
    {
        "name": "here_limit",
        "description": "Limit for here pings",
        "type": 4,
        "required": True
    }
])
async def _slot(ctx: SlashContext, user: discord.User, name: str, category: discord.CategoryChannel, duration: str, everyone_limit: int, here_limit: int):
    await ctx.defer(hidden=True)
    # Check if the user is a server administrator
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(content='`📛You must be a server administrator to use this command.📛`', hidden=True)
        return

    # Check if the user's ID is in the users table and if their expire_time is not 'Expired' and type is 'ShopBot'
    result = users.find_one({"user_id": str(ctx.author.id), "expire_time": {"$ne": "Expired"}, "type": "ShopBot"})

    if result is None:
        await ctx.send(content='`📛You dont have a valid license, or its expired.📛`', hidden=True)
        return
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    # Parse duration
    time_value = int(TIME_UNITS.get(duration))
    time_unit = duration[-1]
    if time_unit not in TIME_UNITS:
        await ctx.send(content=f'Invalid time unit. Use one of these: {", ".join(TIME_UNITS.keys())}', hidden=True)
        return
    duration_seconds = TIME_UNITS[duration]
    # Load the setup data
    with open('setup.json', 'r') as f:
        if f.read().strip():
            f.seek(0)  # reset file position to the beginning
            data = json.load(f)
        else:
            data = {}

    guild_id = str(ctx.guild.id)
    if guild_id in data:
        staff_role_id = data[guild_id]['Staff_Role']
    else:
        await ctx.send(content='Staff role is not set up yet! Use /setup to set it up.', hidden=True)
        return

    guild_id = str(ctx.guild.id)
    if guild_id in data and 'rules' in data[guild_id]:
        rules = data[guild_id]['rules']
    else:
        rules = 'Rules are not set up yet! Use /setup to set them up.'

    # Create the channel
    channel = await ctx.guild.create_text_channel(name, overwrites=overwrites, category=category)
    # Set slowmode delay
    await channel.edit(slowmode_delay=5)
    slot_owner_role_id = data[guild_id]['Slot_Owner_Role']
    slot_owner_role = ctx.guild.get_role(slot_owner_role_id)
    await user.add_roles(slot_owner_role)

    # Calculate end time
    print(datetime.now() + timedelta(seconds=duration_seconds))
    end_time = datetime.now() + timedelta(seconds=duration_seconds)


    # Convert end_time to Unix timestamp
    end_time_unix = int(end_time.timestamp())

    # Store end_time in the JSON file
    with open('slots.json', 'r') as f:
        slots_data = json.load(f)

    slots_data[str(channel.id)] = {
        'guild_id': str(ctx.guild.id),
        'user_id': user.id,
        'duration': duration,
        'everyone_limit': everyone_limit,
        'here_limit': here_limit,
        'end_time_unix': end_time_unix
    }

    with open('slots.json', 'w') as f:
        json.dump(slots_data, f, indent=4)

    await ctx.send(content=f'{user.mention} channel has been created {channel.mention}', hidden=True)
    embed = discord.Embed(title="`💠`Slot Information", color=discord.Color.blue())
    embed.add_field(name="`👑`Slot Owner", value=user.mention, inline=False)
    embed.add_field(name="`📍`Pings", value=f'`{everyone_limit}x` @everyone\n`{here_limit}x` @here', inline=False)
    embed.add_field(name="`⏰`Slot Ends", value=f'<t:{end_time_unix}:R>', inline=False)    
    embed.add_field(name="`🛑`Rules", value=rules, inline=False)
    embed.set_footer(text=os.getenv('FOOTER_TEXT'), icon_url=os.getenv('FOOTER_URL'))
    await channel.send(embed=embed)
    embed1= discord.Embed(title="`🔒`Slot Created", description=f"> Your slot at {channel.mention} has been successfully created!\n\n> Slot ends in: <t:{end_time_unix}:R>", color=0x02FF6D)
    await user.send(embed=embed1)

    await channel.set_permissions(user, read_messages=True, send_messages=True, mention_everyone=True)

    # Calculate remaining time until the slot ends
    remaining_time = (end_time - datetime.now()).total_seconds()

    await asyncio.sleep(duration_seconds)
with open('setup.json', 'r') as f:
    if f.read().strip():
        f.seek(0)  # reset file position to the beginning
        data = json.load(f)
    else:
        data = {}
async def remove_slot_owner_role_and_permission(guild_id, channel_id, user_id, staff_role_id):
    guild = bot.get_guild(int(guild_id))
    try:
        channel = await bot.fetch_channel(int(channel_id))
    except discord.NotFound:
        return
    channel = await bot.fetch_channel(int(channel_id))
    user = await guild.fetch_member(int(user_id))
    staff_role = guild.get_role(int(staff_role_id))

    slot_owner_role_id = data[guild_id]['Slot_Owner_Role']
    slot_owner_role = guild.get_role(int(slot_owner_role_id))

    await user.remove_roles(slot_owner_role)
    await channel.set_permissions(user, read_messages=True, send_messages=False)

    await channel.send(f'`⌛`Your Slot Expired Contact {staff_role.mention} to renew')
    embed = discord.Embed(title="`⌛`Slot Expired", description=f"> Your slot at {channel.mention} had expired!", color=0xAB02FF)
    embed.set_footer(text=os.getenv('FOOTER_TEXT'), icon_url=os.getenv('FOOTER_URL'))
    await user.send(embed=embed)

    with open('slots.json', 'r') as f:
        slots_data = json.load(f)

    del slots_data[str(channel_id)]

    with open('slots.json', 'w') as f:
        json.dump(slots_data, f, indent=4)

async def check_slots():
    while True:  # Run the loop forever
        with open('slots.json', 'r') as f:
            slots_data = json.load(f)

        for channel_id, slot in slots_data.items():
            end_time_unix = slot['end_time_unix']
            end_time = datetime.fromtimestamp(end_time_unix)

            delay = (end_time - datetime.now()).total_seconds()
            if delay <= 0:  # If the slot has already expired, remove it immediately
                guild_id = slot['guild_id']
                user_id = slot['user_id']
                staff_role_id = data[guild_id]['Staff_Role']

                await remove_slot_owner_role_and_permission(guild_id, channel_id, user_id, staff_role_id)

        await asyncio.sleep(10)

user_ping_limits = {}  # Define this at the top of your script

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Load the setup data
    with open('setup.json', 'r') as f:
        data = json.load(f)

    guild_id = str(message.guild.id)
    if guild_id in data and 'Staff_Role' in data[guild_id]:
        staff_role_id = int(data[guild_id]['Staff_Role'])
    else:
        print("Guild ID or Staff_Role not found in data, exiting")
        return

    # Load the slots data
    with open('slots.json', 'r') as f:
        slots_data = json.load(f)

    channel_id = str(message.channel.id)
    if channel_id in slots_data:
        slot = slots_data[channel_id]
    else:
        return

    if message.author.id == slot['user_id']:
        # Load the pings data
        if os.path.exists('pings.json') and os.path.getsize('pings.json') > 0:
            with open('pings.json', 'r') as f:
                user_ping_limits = json.load(f)
        else:
            user_ping_limits = {}

        user_id_str = str(message.author.id)
        guild_id_str = str(message.guild.id)

        if user_id_str not in user_ping_limits:
            user_ping_limits[user_id_str] = {}

        if guild_id_str not in user_ping_limits[user_id_str]:
            # If the user is not in the user_ping_limits dictionary, insert them with the initial limit from the slots table
            user_ping_limits[user_id_str][guild_id_str] = {'@everyone': slot['everyone_limit'], '@here': slot['here_limit']}

        if '@everyone' in message.content:
            user_ping_limits[user_id_str][guild_id_str]['@everyone'] -= 1
            if user_ping_limits[user_id_str][guild_id_str]['@everyone'] >= 0:
                await message.channel.send(f'`❕`Ping detected! You have **{user_ping_limits[user_id_str][guild_id_str]["@everyone"]} ping(s) remaining | Use MM**')
            if user_ping_limits[user_id_str][guild_id_str]['@everyone'] < 0:
                await message.channel.set_permissions(message.author, send_messages=False)
                staff_role = discord.utils.get(message.guild.roles, id=staff_role_id)
                await message.channel.send(f'`❗`{staff_role.mention} {message.author.mention} has exceeded the `@everyone` ping limit`❗`')
            # Save the pings data
            with open('pings.json', 'w') as f:
                json.dump(user_ping_limits, f)
            return

        if '@here' in message.content:
            user_ping_limits[user_id_str][guild_id_str]['@here'] -= 1
            if user_ping_limits[user_id_str][guild_id_str]['@here'] >= 0:
                await message.channel.send(f'`❕`Ping detected! You have **{user_ping_limits[user_id_str][guild_id_str]["@here"]} ping(s) remaining | Use MM**')
            if user_ping_limits[user_id_str][guild_id_str]['@here'] < 0:
                await message.channel.set_permissions(message.author, send_messages=False)
                staff_role = discord.utils.get(message.guild.roles, id=staff_role_id)
                await message.channel.send(f'`❗`{staff_role.mention} {message.author.mention} has exceeded the `@here` ping limit`❗`')
            # Save the pings data
            with open('pings.json', 'w') as f:
                json.dump(user_ping_limits, f)
            return

    await bot.process_commands(message)
@slash.slash(name="nuke", description="Deletes and recreates the current channel.")
async def nuke(ctx: SlashContext):
    # Check if the context has a guild and channel
    if ctx.guild is None or ctx.channel is None:
        await ctx.send("This command can only be used in a guild channel.", hidden=True)
        return

    with open('slots.json', 'r') as f:
        slots_data = json.load(f)

    # Check if the channel is in slots.json
    if str(ctx.channel.id) not in slots_data:
        await ctx.send("This command can only be used in channels that are in slots.json.", hidden=True)
        return

    slot = slots_data[str(ctx.channel.id)]
    everyone_limit = slot['everyone_limit']
    here_limit = slot['here_limit']
    end_time_unix = slot['end_time_unix']

    with open('setup.json', 'r') as f:
        setup_data = json.load(f)

    guild_id = str(ctx.guild.id)
    if guild_id in setup_data:
        rules = setup_data[guild_id]['rules']
    else:
        await ctx.send("The rules for this guild are not defined in setup.json.", hidden=True)
        return

    if ctx.channel.type is discord.ChannelType.text:
        channel = ctx.channel
        category = channel.category
        position = channel.position
        overwrites = channel.overwrites
        topic = channel.topic
        slowmode_delay = channel.slowmode_delay
        nsfw = channel.nsfw

        # Store the channel ID before deleting the channel
        old_channel_id = str(ctx.channel.id)

        await channel.delete()

        # Create the new channel with the same settings
        new_channel = await category.create_text_channel(name=channel.name, position=position, overwrites=overwrites, topic=topic, slowmode_delay=5, nsfw=nsfw)
        
        # Update the channel ID in slots.json using the stored old channel ID
        slots_data[str(new_channel.id)] = slots_data.pop(old_channel_id)

        with open('slots.json', 'w') as f:
            json.dump(slots_data, f, indent=4)

            embed = discord.Embed(title="`💠`Slot Information", color=discord.Color.blue())
            embed.add_field(name="`👑`Slot Owner", value=ctx.author.mention, inline=False)
            embed.add_field(name="`📍`Pings", value=f'`{everyone_limit}x` @everyone\n`{here_limit}x` @here', inline=False)
            embed.add_field(name="`⏰`Slot Ends", value=f'<t:{end_time_unix}:R>', inline=False)    
            embed.add_field(name="`🛑`Rules", value=rules, inline=False)
            embed.set_footer(text=os.getenv('FOOTER_TEXT'), icon_url=os.getenv('FOOTER_URL'))

            await new_channel.send(embed=embed)
            await new_channel.send("Note: This slot was previously nuked")
                # Get the user ID from slots.json
        user_id = slots_data[str(new_channel.id)]['user_id']

        # Fetch the user
        user = await ctx.bot.fetch_user(user_id)

        # Set the permissions for the user
        await new_channel.set_permissions(user, read_messages=True, send_messages=True, mention_everyone=True)
@slash.slash(
    name="hold",
    description="Holds or releases a slot",
    options=[
        create_option(
            name="channel",
            description="The channel to hold or release",
            option_type=7,  # Channel type
            required=True
        ),
        create_option(
            name="hold_type",
            description="Whether to hold or release the slot",
            option_type=3,  # String type
            required=True,
            choices=[
                create_choice(name="hold", value="hold"),
                create_choice(name="release", value="release")
            ]
        )
    ]
)
async def _hold(ctx, channel: discord.abc.GuildChannel, hold_type: str):
    # Check if the user is a server administrator
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(content='`📛You must be a server administrator to use this command.📛`', hidden=True)
        return

    # Check if the user's ID is in the users table and if their expire_time is not 'Expired' and type is 'ShopBot'
    result = users.find_one({"user_id": str(ctx.author.id), "expire_time": {"$ne": "Expired"}, "type": "ShopBot"})

    if result is None:
        await ctx.send(content='`📛You dont have a valid license, or its expired.📛`', hidden=True)
        return

    # Load the setup.json file
    with open('setup.json', 'r') as f:
        data = json.load(f)

    # Get the slot owner role ID
    slot_owner_role_id = data[str(ctx.guild.id)]['Slot_Owner_Role']

    # Get the role object
    slot_owner_role = ctx.guild.get_role(slot_owner_role_id)

    # Load the slots.json file
    with open('slots.json', 'r') as f:
        slots_data = json.load(f)

    # Get the user ID associated with the channel ID
    user_id = slots_data.get(str(channel.id), {}).get('user_id')

    # Fetch the user object
    user = await ctx.guild.fetch_member(int(user_id))

    if hold_type == "hold":
        # Remove the slot owner role from the user
        await user.remove_roles(slot_owner_role)

        # Remove the user's write permissions for the channel
        await channel.set_permissions(user, send_messages=False)

        # Send an embed message to the channel
        embed = discord.Embed(title="`⛔`SLOT ON HOLD", description=f"A Report is open against {user.mention}\n**Do not deal with {user.mention} until the slot is open!**", color=0xFF0602)
        embed.set_thumbnail(url="https://i.imgur.com/wafhR11.png")
        await channel.send(embed=embed)

        # Send a hidden response to the user
        await ctx.send(content="`✅`The slot has been successfully put on hold.", hidden=True)
        await user.send(f"`⛔`Your slot in <#{channel.id}> has been put on hold.")

    elif hold_type == "release":
        # Add the slot owner role back to the user
        await user.add_roles(slot_owner_role)

        # Give the user write permissions for the channel
        await channel.set_permissions(user, read_messages=True, send_messages=True, mention_everyone=True)

        # Send an embed message to the channel
        embed = discord.Embed(title="`💚`Slot Released", description=f"{user.mention}'s slot has been released.", color=0x02FF6D)
        embed.set_thumbnail(url="https://i.imgur.com/4j76IeQ.png")
        await channel.send(embed=embed)

        # Send a hidden response to the user
        await ctx.send(content="`✅`The slot has been successfully released.", hidden=True)
        await user.send(f"`✅`Your slot in <#{channel.id}> has been released.")
# A dictionary to store the timers
timers = {}

@slash.slash(
    name="revoke",
    description="Revokes or restores a user's access to a channel",
    options=[
        create_option(
            name="channel",
            description="The channel to revoke or restore access to",
            option_type=7,  # Channel type
            required=True
        ),
        create_option(
            name="revoke_type",
            description="Whether to revoke or restore access",
            option_type=3,  # String type
            required=True,
            choices=[
                create_choice(name="revoke", value="revoke"),
                create_choice(name="cancel", value="cancel")
            ]
        )
    ]
)
async def _revoke(ctx, channel: discord.abc.GuildChannel, revoke_type: str):
    # Check if the user is a server administrator
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(content='`📛You must be a server administrator to use this command.📛`', hidden=True)
        return

    # Check if the user's ID is in the users table and if their expire_time is not 'Expired' and type is 'ShopBot'
    result = users.find_one({"user_id": str(ctx.author.id), "expire_time": {"$ne": "Expired"}, "type": "ShopBot"})

    if result is None:
        await ctx.send(content='`📛You dont have a valid license, or its expired.📛`', hidden=True)
        return
    # Load the setup.json file
    with open('setup.json', 'r') as f:
        data = json.load(f)

    # Get the slot owner role ID
    slot_owner_role_id = data[str(ctx.guild.id)]['Slot_Owner_Role']

    # Get the role object
    slot_owner_role = ctx.guild.get_role(slot_owner_role_id)

    # Load the slots.json file
    with open('slots.json', 'r') as f:
        slots_data = json.load(f)

    # Get the user ID associated with the channel ID
    user_id = slots_data.get(str(channel.id), {}).get('user_id')

    # Fetch the user object
    user = await ctx.guild.fetch_member(int(user_id))

    if revoke_type == "revoke":
        # Remove the slot owner role from the user
        await user.remove_roles(slot_owner_role)

        # Remove the user's write permissions for the channel
        await channel.set_permissions(user, send_messages=False)

        # Start a timer to delete the channel in 12 hours
        timers[channel.id] = asyncio.create_task(delete_channel_in_12_hours(channel))

        # Send a hidden response to the user
        await ctx.send(content="`⛔`The user's access to the channel has been revoked. The channel will be deleted in 12 hours.", hidden=True)
        await user.send(f"`⛔`Your slot in <#{channel.id}> has been revoked and will be deleted in 12 hours.")

    elif revoke_type == "cancel":
        # If a timer exists for the channel, cancel it
        if channel.id in timers:
            timers[channel.id].cancel()
            del timers[channel.id]

        # Add the slot owner role back to the user
        await user.add_roles(slot_owner_role)

        # Give the user write permissions for the channel
        await channel.set_permissions(user, send_messages=True)

        # Send a hidden response to the user
        await ctx.send(content="`💚`The deletion of the channel has been cancelled. The user's access to the channel has been restored.", hidden=True)
        await user.send(f"`✅`The deletion of the channel in <#{channel.id}> has been cancelled. Your access to the channel has been restored.")

async def delete_channel_in_12_hours(channel):
    await asyncio.sleep(12 * 3600)  # Wait for 12 hours
    await channel.delete()  # Delete the channel
@slash.slash(name="renew", description="Renews a slot", options=[
    {
        "name": "channel",
        "description": "Channel to renew",
        "type": 7,  # Type 7 is for discord.Channel
        "required": True
    },
    {
        "name": "duration",
        "description": "New duration (s = Seconds, d = Days, w = Weeks, m = Months, l = Lifetime)",
        "type": 3,  # Type 3 is for string
        "required": True
    },
    {
        "name": "everyone_limit",
        "description": "Limit for everyone",
        "type": 4,  # Type 4 is for integer
        "required": True
    },
    {
        "name": "here_limit",
        "description": "Limit for here",
        "type": 4,  # Type 4 is for integer
        "required": True
    },
    {
        "name": "user",
        "description": "User for the slot",
        "type": 6,  # Type 6 is for discord.User
        "required": True
    }
])
async def _renew(ctx: SlashContext, channel: discord.TextChannel, duration: str, everyone_limit: int, here_limit: int, user: discord.User):
    await ctx.defer(hidden=True)
    # Check if the user is a server administrator
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(content='`📛You must be a server administrator to use this command.📛`', hidden=True)
        return

    # Check if the user's ID is in the users table and if their expire_time is not 'Expired' and type is 'ShopBot'
    result = users.find_one({"user_id": str(ctx.author.id), "expire_time": {"$ne": "Expired"}, "type": "ShopBot"})

    if result is None:
        await ctx.send(content='`📛You dont have a valid license, or its expired.📛`', hidden=True)
        return

    # Load the slots data
    with open('slots.json', 'r') as f:
        slots_data = json.load(f)
    # Parse duration
    time_value = int(duration[:-1])
    time_unit = duration[-1]
    if time_unit not in TIME_UNITS:
        await ctx.send(content=f'Invalid time unit. Use one of these: {", ".join(TIME_UNITS.keys())}', hidden=True)
        return
    duration_seconds = time_value * TIME_UNITS[time_unit]
    # Calculate new end time
    end_time = datetime.now() + timedelta(seconds=duration_seconds)

    # Convert end_time to Unix timestamp
    end_time_unix = int(end_time.timestamp())

    # Check if the channel ID exists in the slots data
    if str(channel.id) in slots_data:
        # Update the duration, end time, everyone_limit, and here_limit in the slots data
        slots_data[str(channel.id)]['duration'] = duration
        slots_data[str(channel.id)]['end_time_unix'] = end_time_unix
        slots_data[str(channel.id)]['everyone_limit'] = everyone_limit
        slots_data[str(channel.id)]['here_limit'] = here_limit

        # Load the setup data
        with open('setup.json', 'r') as f:
            setup_data = json.load(f)

        # Fetch the slot owner role
        guild_setup_data = setup_data[str(ctx.guild.id)]
        slot_owner_role_id = guild_setup_data['Slot_Owner_Role']
        slot_owner_role = ctx.guild.get_role(int(slot_owner_role_id))

        # Set the permissions for the user
        await channel.set_permissions(user, read_messages=True, send_messages=True, mention_everyone=True)

        # Assign the slot owner role to the user
        await user.add_roles(slot_owner_role)

        # If the slot has already ended, assign back the permissions to the channel and the slot owner role to the user
        if datetime.now().timestamp() > slots_data[str(channel.id)]['end_time_unix']:
            guild_id = slots_data[str(channel.id)]['guild_id']
            user_id = slots_data[str(channel.id)]['user_id']
            staff_role_id = setup_data[guild_id]['Staff_Role']
            await remove_slot_owner_role_and_permission(guild_id, channel.id, user_id, staff_role_id)

        # Save the updated slots data back to the 'slots.json' file
        with open('slots.json', 'w') as f:
            json.dump(slots_data, f, indent=4)

        await ctx.send(content=f'{user.mention} slot has been renewed {channel.mention}', hidden=True)
        embed= discord.Embed(title="`🔒`Slot Renewed", description=f"> Your slot at {channel.mention} has been successfully renewed!\n\n> Slot ends in: <t:{end_time_unix}:R>", color=0x02FF6D)
        embed.set_footer(text=os.getenv('FOOTER_TEXT'), icon_url=os.getenv('FOOTER_URL'))
        await user.send(embed=embed)
    else:
        # If the channel ID does not exist in the slots data, create a new entry
        slots_data[str(channel.id)] = {
            "guild_id": str(ctx.guild.id),
            "user_id": user.id,
            "duration": duration,
            "everyone_limit": everyone_limit,
            "here_limit": here_limit,
            "end_time_unix": end_time_unix
        }

        # Load the setup data
        with open('setup.json', 'r') as f:
            setup_data = json.load(f)

        # Fetch the slot owner role
        guild_setup_data = setup_data[str(ctx.guild.id)]
        slot_owner_role_id = guild_setup_data['Slot_Owner_Role']
        slot_owner_role = ctx.guild.get_role(int(slot_owner_role_id))

        # Set the permissions for the user
        await channel.set_permissions(user, read_messages=True, send_messages=True, mention_everyone=True)

        # Assign the slot owner role to the user
        await user.add_roles(slot_owner_role)

        # Save the new slots data back to the 'slots.json' file
        with open('slots.json', 'w') as f:
            json.dump(slots_data, f, indent=4)

        await ctx.send(content=f'{user.mention} slot has been created {channel.mention}', hidden=True)
        embed= discord.Embed(title="`🔒`Slot Renewed", description=f"> Your slot at {channel.mention} has been successfully renewed!\n\n> Slot ends in: <t:{end_time_unix}:R>", color=0x02FF6D)
        embed.set_footer(text=os.getenv('FOOTER_TEXT'), icon_url=os.getenv('FOOTER_URL'))
        await user.send(embed=embed)

TIME_UNITS = {"s": 1, "d": 86400, "w": 604800, "m": 2629743, "l": 3155695200}

@slash.slash(name="myslot", description="Shows info about your slot.")
async def myslot(ctx: SlashContext):
    user_id = str(ctx.author.id)
    guild_id = str(ctx.guild.id)

    with open('slots.json', 'r') as f:
        slots = json.load(f)

    with open('pings.json', 'r') as f:
        pings = json.load(f)

    slot = None
    channel_id = None  # Initialize channel_id
    for key, slot_info in slots.items():  # Get both key and value from the dictionary
        if str(slot_info['user_id']) == user_id and str(slot_info['guild_id']) == guild_id:
            slot = slot_info
            channel_id = key  # Set the key as the channel_id
            break

    if slot:
        duration = slot['duration']
        end_time_unix = slot['end_time_unix']

        # Get the channel and category information
        channel = bot.get_channel(int(channel_id))
        category = channel.category.name if channel.category else 'No Category'

        # Get the user's pings
        user_pings = pings.get(guild_id, {}).get(user_id, {}).get(channel_id, {"@everyone": 0, "@here": 0})

        # Convert duration to seconds for calculation
        duration_seconds = int(duration[:-1]) * TIME_UNITS[duration[-1]]
        # Calculate creation time
        creation_time_unix = end_time_unix - duration_seconds
        creation_time = datetime.fromtimestamp(creation_time_unix)

        # Convert creation_time to Unix timestamp
        creation_time_unix = int(creation_time.timestamp())

        embed = discord.Embed(title="Slot Information", color=0xC10CF6)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.add_field(name="`📑`Channel", value=f"<#{channel_id}>", inline=False)
        embed.add_field(name="`📁`Category", value=category, inline=False)
        embed.add_field(name="`🏁`Slot Creation Date", value=f"<t:{creation_time_unix}:R>", inline=False)
        embed.add_field(name="`⛔`Slot End Time", value=f"<t:{end_time_unix}:R>", inline=False)
        embed.add_field(name="`📌`Used @everyone pings", value=user_pings["@everyone"], inline=False)
        embed.add_field(name="`📍`Used @here pings", value=user_pings["@here"], inline=False)
        embed.set_footer(text=os.getenv('FOOTER_TEXT'), icon_url=os.getenv('FOOTER_URL'))
        embed.timestamp = datetime.utcnow()

        await ctx.send(embed=embed)
    else:
        await ctx.send("`⛔`You don't have any slots.", hidden=True)
bot.run(TOKEN)