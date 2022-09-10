"""Main script that should be executed to start bot execution"""
import logging
import sys

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import bot

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("Main")


intents = discord.Intents.default()
discord_bot = commands.Bot(
    intents=intents, command_prefix=bot.config.prefix(), help_command=None
)

# Scheduling Stuff
SCHEDULER = None

# Scheduled commands with their respective triggers can be set here:
scheduled_commands = {
    "events": CronTrigger(day_of_week="sun", hour="21", minute="20", second="0"),
    "event_results": CronTrigger(day_of_week="wed", hour="18", minute="00", second="0"),
}


def schedule_command(command):
    """Higher-order function wrapper that creates a callable function for a bot command

    Args:
        command (str): name of the command
    """

    async def func():
        """The actual function that's called by the apscheduler"""
        channel = discord_bot.get_channel(bot.config.schedule_channel())
        message = await channel.send(f"!{command}")
        ctx = await discord_bot.get_context(message)
        await ctx.invoke(discord_bot.get_command(command))

    return func


@discord_bot.event
async def on_ready():
    """Called when the client is done preparing the data received from Discord"""
    logger.info("Discord Init complete!")

    # Now, register all cogs:
    for cog in bot.enabled_cogs:
        discord_bot.add_cog(cog(discord_bot))
    logger.info("\nPrefix: '%s'", bot.config.prefix())
    available_cogs = [
        c.name
        for cog in discord_bot.cogs
        for c in discord_bot.get_cog(cog).get_commands()
    ]
    logger.info("Available Commands: %s", available_cogs)

    logger.info("Now starting scheduler...")
    channel = discord_bot.get_channel(bot.config.schedule_channel())
    SCHEDULER.start()

    formatted_schedule = "\n\n".join(
        [
            f"{job.name} :arrow_right:  {job.trigger}\nNext: {job.next_run_time}\n"
            for job in SCHEDULER.get_jobs()
        ]
    )

    await channel.send(
        f"The following scheduled messages are set up for this channel: \n{formatted_schedule}\n"
        f"_This message will self-destruct in 10 seconds._",
        delete_after=10.0,
    )
    logger.info("Scheduler initiated!")


@discord_bot.event
async def on_connect():
    """Called when the client has successfully connected to Discord."""
    logger.debug("Adding Scheduled Functions...")
    for message, schedule in scheduled_commands.items():
        SCHEDULER.add_job(schedule_command(message), schedule, name=message)


@discord_bot.event
async def on_disconnect():
    """Called when the client has disconnected from Discord."""
    logger.debug("Disconnected from Discord! Flushing jobs...")
    for job in SCHEDULER.get_jobs():
        #job.remove()
        pass


if __name__ == "__main__":
    logger.info("Initializing scheduler...")
    SCHEDULER = AsyncIOScheduler()

    logger.info("Running Bot...")
    discord_bot.run(bot.config.bot_token())
