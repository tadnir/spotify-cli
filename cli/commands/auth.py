import os
import json
import time

import click
import beaupy

from ..utils import Spotify
from ..utils.constants import *
from ..utils.functions import build_auth_url


@click.command(options_metavar='[<options>]')
@click.option(
    '--client-id', type=str, metavar='<str>', default='',
    help=(
        'When provided, authenticates the CLI using your own application ID '
        'and secret (helps avoid API rate limiting issues).'
    )
)
@click.option(
    '--client-secret', type=str, metavar='<str>', default='',
    help='Required if --client-id is provided.'
)
def login(client_id='', client_secret=''):
    """Authorize spotify-cli to access the Spotify API."""
    # verify both creds are provided
    if client_id or client_secret:
        if client_id and client_secret:
            click.echo(
                'Authenticating with provided Client ID and secret.\n'
                'Please ensure that the URL below is listed as a valid '
                'redirect URI in your Spotify application:\n\n{}\n'
                .format(REDIRECT_URI)
            )
        else:
            click.echo(
                'Please provide both the Client ID and secret.',
                err=True
            )
            return

    config = Spotify.get_config()
    if config.get('client_id') and not client_id:
        reuse_creds = click.confirm(
            'You used a custom Client ID and secret to authenticate last time. '
            'Use these again?\n'
            '(Type "n" to revert to the default ID and secret)',
            default=True,
        )
        if not reuse_creds:
            client_id = ''
            client_secret = ''
            click.echo('Removing custom client ID and secret.\n')
        else:
            client_id = config.get('client_id')
            client_secret = config.get('client_secret')

    Spotify.update_config({
        'client_id': client_id,
        'client_secret': client_secret,
    })

    # select scopes
    enabled_scopes = Spotify.get_config().get('auth_scopes', [])
    choices = []
    for scope in AUTH_SCOPES_MAPPING:
        if scope['value'] == 'default':
            continue
        choices.append({
            'name': scope['name'],
            'checked': scope['name'] in enabled_scopes,
        })

    click.echo(
        'By default, spotify-cli will enable reading & '
        'modifying the playback state.\n'
    )
    click.echo('Please select which additional features you want to authorize.')
    choice = beaupy.select_multiple(options=choices, preprocessor=lambda c: c["name"])

    # confirm
    additional_scopes = [c["name"] for c in choice]
    click.echo(
        '\n{} features selected. This will overwite your existing credentials.'
        .format(len(additional_scopes))
    )
    click.confirm('Proceed with these settings?', default=True, abort=True)

    # handle auth and save credentials
    import webbrowser
    url = build_auth_url(additional_scopes, client_id)
    webbrowser.open(url)
    click.echo(
        '\nGo to the following link in your browser:\n\n\t{}\n'
        .format(url)
    )
    auth_code = input('Enter verification code: ')
    click.echo('\nObtaining access token...')
    Spotify.refresh(auth_code)
    Spotify.update_config({'auth_scopes': additional_scopes})
    click.echo('Credentials saved to {}'.format(CREDS_PATH))
    return


@click.command()
@click.option(
    '-v', '--verbose', is_flag=True,
    help='Output more info (i.e. credential storage)'
)
def status(verbose):
    """Show who's logged in."""
    user_data = Spotify.request('me', method='GET')
    click.echo('Logged in as {}'.format(user_data['display_name']))
    if verbose:
        click.echo('Credentials stored in {}'.format(CREDS_PATH))
    return


# CLI group
@click.group(
    options_metavar='[<options>]',
    subcommand_metavar='<command>'
)
def auth():
    """Manage user authentication for spotify-cli."""
    pass


auth.add_command(login)
auth.add_command(status)
