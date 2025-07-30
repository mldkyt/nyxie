import os
from mastodon import Mastodon

Mastodon.create_app(
    'Ai',
    api_base_url='https://ice.lunya.pet',
    to_file='mastodon/clientcred.secret'
)


if os.path.exists("mastodon/usercred.secret"):
    mastodon = Mastodon(access_token="mastodon/usercred.secret")
else:
    mastodon = Mastodon(client_id = 'mastodon/clientcred.secret',)
    print(mastodon.auth_request_url())
    mastodon.log_in(
        code=input("oauth2 code: "),
        to_file="mastodon/usercred.secret"
    )

me = mastodon.me()
print(f"Logged in as {me.display_name}")
