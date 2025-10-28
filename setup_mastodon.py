#!/bin/python3
import os.path
from getpass import getpass

from mastodon import Mastodon

from constants import FEDI_INSTANCE

if not os.path.exists("data/clientcred"):
    Mastodon.create_app(
        'ai',
        to_file='data/clientcred',
        api_base_url=f'https://{FEDI_INSTANCE}'
    )

if not os.path.exists("data/usercred"):
    username = input("Username ")
    password = getpass("Password ")

    mastodon = Mastodon(client_id='data/clientcred')
    mastodon.log_in(
        username,
        password,
        to_file='data/usercred'
    )
else:
    mastodon = Mastodon(access_token='data/usercred', api_base_url=f'https://{FEDI_INSTANCE}')

me = mastodon.me()
print(f"Logged in as {me.acct}")
