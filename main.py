import nextcord
from nextcord.ext import commands
import os
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()

intents = nextcord.Intents.default()
intents.messages = True
intents.message_content = True

client = commands.Bot(command_prefix=">", intents=intents)

@client.event
async def on_ready():
    print(f"{client.user.name} is online")
    

if os.path.exists("./guilds.json"):
    with open("./guilds.json", "r") as f:
        setup_data = json.load(f)
else:
    setup_data = {}


import asyncio

@client.command()
async def setup(ctx):
    try:
        if str(ctx.guild.id) in setup_data:
            if str(ctx.author.id) != setup_data[str(ctx.guild.id)]["client_id"]:
                await ctx.send("Only the user who initially set up the project can use the setup command in this guild.")
                return
            else:
                await ctx.send("You have already set up your project in this guild.")
                return

        await ctx.send("What would you like to be the name of your root file?")
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel
        root_file_name_msg = await client.wait_for('message', check=check, timeout=60)
        root_file_name = root_file_name_msg.content

        user_id = str(ctx.author.id)
        project_name = root_file_name  # Use the root file name as project name
        project_folder = f"./projects/{user_id}/{project_name}"
        os.makedirs(project_folder, exist_ok=True)

        await ctx.send("Setting up this project will delete existing channels. Are you sure you want to proceed?")
        confirmation_message = await ctx.send("React with ✅ to confirm or ❌ to cancel.")

        await confirmation_message.add_reaction('✅')  
        await confirmation_message.add_reaction('❌')

        def check_reaction(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirmation_message.id

        reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check_reaction)

        if str(reaction.emoji) == '❌':
            await ctx.send("Setup cancelled.")
            return

        # Delete existing channels and categories
        for category in ctx.guild.categories:
            await category.delete()
        
        for channel in ctx.guild.channels:
            await channel.delete()

        # Create a category named "core"
        core_category = await ctx.guild.create_category("core")

        # Create new channels inside the "core" category
        chat_channel = await core_category.create_text_channel("chat-channel")
        console_channel = await core_category.create_text_channel("console")
        env_channel = await core_category.create_text_channel("env")
        git_ignore_channel = await core_category.create_text_channel("git-ignore")

        # Create .gitignore file
        with open(f"{project_folder}/.gitignore", "w") as f:
            f.write("# Add files or directories to ignore in your Git repository")

        # Create .env file
        env_file_path = os.path.join(project_folder, ".env")
        open(env_file_path, 'a').close()

        await asyncio.sleep(5)  # Wait for 5 seconds to ensure channels are created

        await chat_channel.send("Setup completed successfully!")  # Send message in chat_channel

        # Update setup_data
        setup_data[str(ctx.guild.id)] = {"client_id": str(ctx.author.id), "project_name": project_name}
        with open("./guilds.json", "w") as f:
            json.dump(setup_data, f)

    except nextcord.Forbidden:
        await ctx.send("I do not have permission to delete channels or categories.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")






@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.name == "chat-channel":
        return

    # Handling messages in "git-ignore" channel
    if message.channel.name == "git-ignore":
        guild_id = str(message.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
            gitignore_path = os.path.join(project_folder, ".gitignore")
            with open(gitignore_path, "a") as f:
                f.write(f"{message.content}\n")
            await message.add_reaction("✅")
            return  # Exit the function after handling the git-ignore message

    # Handling messages in "env" channel
    if message.channel.name == "env":
        guild_id = str(message.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
            env_file_path = os.path.join(project_folder, ".env")
            with open(env_file_path, "a") as f:
                f.write(f"{message.content}\n")
            await message.add_reaction("✅")
            return  # Exit the function after handling the env message

    # Handling messages in "console" channel
    if message.channel.name == "console":
        guild_id = str(message.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
            try:
                result = subprocess.run(message.content, cwd=project_folder, shell=True, capture_output=True, text=True)
                console_output = result.stdout.strip()
                if console_output:
                    console_channel = nextcord.utils.get(message.guild.channels, name="console")
                    await console_channel.send(console_output)
                else:
                    await message.channel.send("No output generated.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")
            return  

  
    guild_id = str(message.guild.id)
    if guild_id in setup_data:
        project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
        category_folder = os.path.join(project_folder, message.channel.category.name) if message.channel.category else project_folder

        channel_name = message.channel.name.lower()
        if channel_name.endswith("-py"):
            file_extension = ".py"
        elif channel_name.endswith("-java"):
            file_extension = ".java"
        elif channel_name.endswith("-js"):
            file_extension = ".js"
        else:
            file_extension = ".txt"

        file_name = f"{channel_name.removesuffix('-py').removesuffix('-java').removesuffix('-js')}{file_extension}"
        file_path = os.path.join(category_folder, file_name)

        # Check if the file path exists and create the file if it doesn't
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "a") as f:
            f.write(message.content + "\n")

        # Add reaction for feedback
        await message.add_reaction("✅")  # Added reaction

    await client.process_commands(message)




@client.event
async def on_message_edit(before, after):
    if before.author == client.user:
        return
    
    if before.channel.name == "git-ignore":
        guild_id = str(before.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}"
            gitignore_path = os.path.join(project_folder, ".gitignore")
            with open(gitignore_path, "r") as f:
                lines = f.readlines()
            
            with open(gitignore_path, "w") as f:
                edited_content = f"{after.content}\n"
                for line in lines:
                    if line.strip() != before.content:
                        f.write(line)
                    else:
                        f.write(edited_content)

            await after.add_reaction("✏️") 

    if before.channel.name == "env":
        guild_id = str(before.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
            env_file_path = os.path.join(project_folder, ".env")
            with open(env_file_path, "r") as f:
                lines = f.readlines()
            
            with open(env_file_path, "w") as f:
                edited_content = f"{after.content}\n"
                for line in lines:
                    if line.strip() != before.content:
                        f.write(line)
                    else:
                        f.write(edited_content)

            await after.add_reaction("✏️") 

    # Check if the message was edited in a channel corresponding to files
    if before.channel.category and before.channel.category.name != "git-ignore" and before.channel.name != "console":
        guild_id = str(before.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}"
            category_folder = os.path.join(project_folder, before.channel.category.name)
            
            channel_name = before.channel.name.lower()
            if channel_name.endswith("py"):
                file_extension = ".py"
            elif channel_name.endswith("java"):
                file_extension = ".java"
            elif channel_name.endswith("js"):
                file_extension = ".js"
            else:
                file_extension = ".txt"
            
            file_name = f"{channel_name.removesuffix('-py').removesuffix('-java').removesuffix('-js')}{file_extension}"
            file_path = os.path.join(category_folder, file_name)

            # If the edited message was in a file channel and it exists, update the file
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    lines = f.readlines()
                
                with open(file_path, "w") as f:
                    edited_content = after.content + "\n"
                    for line in lines:
                        if line.strip() != before.content:
                            f.write(line)
                        else:
                            f.write(edited_content)

                # Add reaction for edit feedback
                await after.add_reaction("✏️") 

@client.event
async def on_message_delete(message):
    if message.author == client.user:
        return
    
    if message.channel.name == "git-ignore":
        guild_id = str(message.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}"
            gitignore_path = os.path.join(project_folder, ".gitignore")
            with open(gitignore_path, "r") as f:
                lines = f.readlines()
            
            with open(gitignore_path, "w") as f:
                for line in lines:
                    if line.strip() != message.content:
                        f.write(line)

    if message.channel.name == "env":
        guild_id = str(message.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
            env_file_path = os.path.join(project_folder, ".env")
            with open(env_file_path, "r") as f:
                lines = f.readlines()
            
            with open(env_file_path, "w") as f:
                for line in lines:
                    if line.strip() != message.content:
                        f.write(line)

    # Check if the message was deleted in a channel corresponding to files
    if message.channel.category and message.channel.category.name != "git-ignore" and message.channel.name != "console":
        guild_id = str(message.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}"
            category_folder = os.path.join(project_folder, message.channel.category.name)
            
            channel_name = message.channel.name.lower()
            if channel_name.endswith("py"):
                file_extension = ".py"
            elif channel_name.endswith("java"):
                file_extension = ".java"
            elif channel_name.endswith("js"):
                file_extension = ".js"
            else:
                file_extension = ".txt"
            
            file_name = f"{channel_name.removesuffix('-py').removesuffix('-java').removesuffix('-js')}{file_extension}"
            file_path = os.path.join(category_folder, file_name)

            # If the deleted message was in a file channel and it exists, remove the corresponding line
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    lines = f.readlines()
                
                with open(file_path, "w") as f:
                    for line in lines:
                        if line.strip() != message.content:
                            f.write(line)



@client.event
async def on_guild_channel_create(channel):
    if isinstance(channel, nextcord.CategoryChannel):
        guild_id = str(channel.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
            category_folder = os.path.join(project_folder, channel.name)
            os.makedirs(category_folder, exist_ok=True)

    elif isinstance(channel, nextcord.TextChannel):
        guild_id = str(channel.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
            category_folder = os.path.join(project_folder, channel.category.name)
            
            channel_name = channel.name.lower()
            if channel_name.endswith("py"):
                file_extension = ".py"
            elif channel_name.endswith("java"):
                file_extension = ".java"
            elif channel_name.endswith("js"):
                file_extension = ".js"
            else:
                file_extension = ".txt"
            
            file_name = f"{channel_name.removesuffix('-py').removesuffix('-java').removesuffix('-js')}{file_extension}"
            file_path = os.path.join(category_folder, file_name)
            open(file_path, 'a').close()

@client.event
async def on_guild_channel_delete(channel):
    if isinstance(channel, nextcord.CategoryChannel):
        guild_id = str(channel.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
            category_folder = os.path.join(project_folder, channel.name)
            if os.path.exists(category_folder):
                os.rmdir(category_folder)

    elif isinstance(channel, nextcord.TextChannel):
        guild_id = str(channel.guild.id)
        if guild_id in setup_data:
            project_folder = f"./projects/{setup_data[guild_id]['client_id']}/{setup_data[guild_id]['project_name']}"
            category_folder = os.path.join(project_folder, channel.category.name)
            channel_name = channel.name.lower()
            if channel_name.endswith("-py") or channel_name.endswith("-java") or channel_name.endswith("-js"):
                file_extension = ".py" if channel_name.endswith("-py") else (".java" if channel_name.endswith("-java") else ".js")
                file_name = f"{channel_name.removesuffix('-py').removesuffix('-java').removesuffix('-js')}{file_extension}"
            else:
                file_name = f"{channel.name}.txt"

            file_path = os.path.join(category_folder, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)



client.run(os.getenv('token'))