import time

import click

from ..utils import Spotify
from ..utils.parsers import *
from ..utils.functions import cut_string
from ..utils.exceptions import *


@click.command(options_metavar='[<options>]')
@click.option(
    '-l', '--limit', type=int, default=10,
    help='Number of items to show.',
    metavar='<int>'
)
@click.option(
    '--raw', is_flag=True,
    help='Output raw API response.'
)
def lists(raw=False, limit=10, _return_parsed=False):
    """Search for any Spotify content."""
    import urllib.parse as ul
    from tabulate import tabulate

    pager = Spotify.Pager(
        'me/playlists',
        limit=limit,
        # content_callback=lambda c: c['playlists']
    )
    if raw:
        import json
        click.echo(json.dumps(pager.content))
        return pager.content

    commands = {
        0: ['[p]lay', '[s]ave'],
        1: '[Ctrl+C] exit\n',
    }

    headers = ['#', 'Playlist', 'Created by', '# of tracks']
    click.echo('\nYour Playlists')
    parsed_content = {}
    end_search = False

    print_table = True
    while not end_search:
        table = []
        for i, item in enumerate(pager.items):
            index = pager.offset + 1 + i
            parsed_item = {
                '#': index,
                'Playlist': cut_string(item['name'], 50),
                'Created by': cut_string(
                    item['owner'].get('display_name'), 30
                ),
                '# of tracks': item['tracks'].get('total', 0),
                'uri': item['uri'],
                'id': item['id'],
            }
            parsed_content[index] = parsed_item
            row = [parsed_item[h] for h in headers]
            table.append(row)

        if len(table) == 0:
            click.echo('No data available for your search query.', err=True)
            return

        click.echo('\n', nl=False)
        if print_table:
            click.echo(tabulate(table, headers=headers))

        response = click.prompt(
            '\nActions:\n'
            '[n]ext/[b]ack\n'
            '{} #[,...]\n'
            '{}'
            .format(
                '/'.join(commands[0]),
                commands.get(1, '')
            )
        ).lower()

        # if any error in the middle, do not print table
        print_table = False

        cmd = response.split(' ')[0]
        if cmd == 'n':
            try:
                pager.next()
                print_table = True
            except PagerLimitReached:
                click.echo('\nThere are no more results to display.')
                continue

        elif cmd == 'b':
            try:
                pager.previous()
                print_table = True
            except PagerPreviousUnavailable:
                click.echo('\nYou are already at the first page.')
                continue
        else:
            # parse selection
            try:
                indices_str = response.split(' ')[1]
            except IndexError:
                _display_input_err()
                continue

            indices = indices_str.split(',')
            selected = []
            for i in indices:
                try:
                    selected.append(parsed_content[int(i)])
                except (ValueError, IndexError, KeyError):
                    continue

            # parse command
            click.echo('\n', nl=False)
            if len(selected) == 0:
                _display_input_err()
                continue

            try:
                conf_msg = _get_conf_msg(cmd, indices_str)
            except InvalidInput as e:
                click.echo(e.message, err=True)
                continue

            conf = click.confirm(conf_msg, default=True)
            if not conf:
                pass

            elif cmd == 'p':
                from cli.commands.play import play
                req_data = {'context_uri': selected[0]['uri']}
                play.callback(data=req_data, quiet=True)
                click.echo(
                    'Now playing: {}'
                    .format(selected[0]["Playlist"])
                )

            elif cmd == 's':
                requests = _format_save_reqs(selected)
                reqs = Spotify.multirequest(requests)
                click.echo(
                    '{} playlists saved.'
                    .format(len(selected))
                )

            print_table = True
            end_search = not click.confirm(
                '\nContinue searching?', default=True
            )

    return


def _get_conf_msg(cmd, indices_str):
    mapping = {
        'p': (
            'Play the selected playlist? ({})'
            .format(indices_str.split(',')[0])
        ),
        'q':  (
            'Queue the selected playlist? ({})'
            .format(indices_str.split(',')[0])
        ),
        's': (
            'Save the selected playlist/s? ({})'
            .format(indices_str)
        ),
    }
    cmd_map = mapping.get(cmd)
    if not cmd_map:
        raise InvalidInput('\nCommand [{}] not found.'.format(cmd))
    return cmd_map


def _format_save_reqs(selected):
    base_req = {
        'method': 'PUT',
        'handle_errs': {
            403: (AuthScopeError, {'required_scope_key': 'user-modify'})
        }
    }
    requests = []
    for s in selected:
        r = base_req.copy()
        r['endpoint'] = 'playlists/{}/followers'.format(s['id'])
        r['data'] = {'public': True}

        requests.append(r)

    return requests


def _display_input_err():
    click.echo(
        'Input error! Please try again.\n'
        'Format: <command> <#s comma delimited>\n'
        'Example: q 3,2,1',
        err=True
    )
