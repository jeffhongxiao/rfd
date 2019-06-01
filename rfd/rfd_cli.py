from __future__ import unicode_literals


import logging
import os
import sys
import click
from colorama import init, Fore, Style
from rfd.api import parse_threads, get_threads, get_posts
from rfd.__version__ import version as current_version

init()

logging.getLogger()
logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())


def get_version():
    return "rfd " + current_version


def get_terminal_width():
    _, columns = os.popen("stty size", "r").read().split()
    return int(columns)


def get_vote_color(score):
    if score > 0:
        return Fore.GREEN + " [+" + str(score) + "] "
    if score < 0:
        return Fore.RED + " [" + str(score) + "] "
    return Fore.BLUE + " [" + str(score) + "] "


@click.group(invoke_without_command=True)
@click.option("--version/--no-version", default=False)
@click.pass_context
def cli(ctx, version):
    """Welcome to the RFD CLI. (RedFlagDeals.com)"""
    if version:
        click.echo(get_version())
    elif not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


@cli.command("version")
def display_version():
    click.echo(get_version())


@cli.command(short_help="Displays posts in a specific thread.")
@click.option(
    "--start",
    default=0,
    help="(for incremental crawling): the post number to start from, default 0 means starting from 0th post.",
)
@click.option(
    "--count", 
    default=0, 
    help="Number of posts to be crawled. Default is 0, for all posts"
)
@click.argument("post_id")
def posts(post_id, start, count):
    """Displays posts in a specific thread.

    post_id can be a full url or post id only

    Example:

    \b
    url: https://forums.redflagdeals.com/koodo-targeted-public-mobile-12-120-koodo-5gb-40-no-referrals-2173603
    post_id: 2173603
    """

    check_input(count)
    check_input(start)

    try:
        # click.echo("-" * get_terminal_width())
        
        # all_posts_generator = get_posts(post=post_id, start=start, count=count)
        # for post in all_posts_generator:
        for post in get_posts(post=post_id, start=start, count=count):
            click.echo(
                " -"
                + get_vote_color(post.get("score"))
                + Fore.RESET
                # + post.get("body")
                + Fore.YELLOW
                + " ({})".format(post.get("user"))
            )
            click.echo(Style.RESET_ALL)
    except ValueError:
        click.echo("Invalid post id.")
        sys.exit(1)
    except AttributeError:
        click.echo("AttributeError: RFD API did not return expected data.")

def check_input(number):
    if number < 0:
        click.echo("Invalid input: %d" % number)
        sys.exit(1)


@cli.command(short_help="Displays threads in the specified forum.")
@click.option("--limit", default=10, help="Number of topics.")
@click.argument("forum_id", default=9)
def threads(limit, forum_id):
    """Displays threads in the specified forum id. Defaults to 9.

    Popular forum ids:

    \b
    9 \t hot deals
    14 \t computer and electronics
    15 \t offtopic
    17 \t entertainment
    18 \t food and drink
    40 \t automotive
    53 \t home and garden
    67 \t fashion and apparel
    74 \t shopping discussion
    88 \t cell phones
    """
    _threads = parse_threads(get_threads(forum_id, limit), limit)
    for i, thread in enumerate(_threads, 1):
        click.echo(
            " "
            + str(i)
            + "."
            + get_vote_color(thread.get("score"))
            + Fore.RESET
            + thread.get("title")
        )
        click.echo(Fore.BLUE + " {}".format(thread.get("url")))
        click.echo(Style.RESET_ALL)


if __name__ == "__main__":
    cli()
