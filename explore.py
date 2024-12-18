# %%
import atproto
import dotenv
import matplotlib.pyplot as plt
import os
import pandas as pd
import requests
import time

# %% Login
class AtProtoClient:
    '''Client with authentication'''
    def __init__(self):
        dotenv.load_dotenv('.env')
        self.username = os.getenv('BSKY_USERNAME')
        self.password = os.getenv('BSKY_PASSWORD')
        self.client = atproto.Client()

    def authenticate(
        self,
        username: str | None = None,
        password: str | None = None,
    ):
        '''Username and password to authenticate client. Default to .env'''
        if username is None:
            username = self.username
        if password is None:
            password = self.password
        # Assign to the class
        self.profile = self.client.login(
            login=username,
            password=password,
        )

    def get_followers(
        self,
        handle: str | None = None,
        batch_size: int = 100,
        max_limit: int | None = None,
        delay: float = 0.5,
    ) -> dict:
        if handle is None:
            handle = self.username
        
        #
        followers: list[dict] = []
        cursor=None
        first_iteration = True

        while (cursor is not None) or first_iteration:
            first_iteration = False
            print(f'Finding... {len(followers)=}')
            if max_limit is not None:
                batch_size = min(
                    batch_size,
                    (max_limit - len(followers)),
                )
            # Fetch the current page
            response = self.client.get_followers(
                actor=handle,
                cursor=cursor,
                limit=batch_size,
            )
            # Add set of followers w/ info to growing list
            print(f'\tFound {len(response.followers)=}')
            followers.extend(
                dict(
                    handle=follower.handle,
                    did=follower.did,
                    created_at=follower.created_at,
                    description=follower.description,
                    display_name=follower.display_name,
                )
                for follower in response.followers
            )
            # Check if reached end or limit
            if max_limit and (len(followers) >= max_limit):
                break
            cursor = response.cursor
            if not cursor:
                print(f'Cursor ended')
                break

            time.sleep(delay)

        return followers
        


# %%
def get_profile_info(handle: str) -> dict[str] | None:
    url: str = (
        'https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?'
        f'actor={handle}'
    )

    try:
        response = requests.get(url)
        # Raise an exception for bad status codes
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return None


# %% Plots
def get_dataframe(followers: list[dict]):
    df = pd.DataFrame(followers)
    # Lazily assuming this exists
    df.created_at
    df.created_at = pd.to_datetime(df.created_at)
    
    return df

def plot_profiles(
    df: pd.DataFrame,
    kind: str | None = None,
):
    # Resample the data by day and count the number of accounts created
    df_resampled = df.set_index('created_at')
    daily_counts = df_resampled.resample('D').size()

    f, ax = plt.subplots()
    ax.set_title('Accounts Created Over Time')
    ax.set_xlabel('Date')

    if kind and kind.lower() == 'cdf':
        cumulative_counts = daily_counts.cumsum()
        # Normalize cumulative counts to get the CDF
        plotting_data = cumulative_counts / cumulative_counts.max()
        ax.set_ylabel('CDF')
    else:
        plotting_data = daily_counts
        ax.set_ylabel('Number of Accounts Created')
        
    
    ax.plot(plotting_data)
    f.autofmt_xdate()
    plt.show()


# %%
if __name__ == '__main__':
    my_client = AtProtoClient()
    my_client.authenticate()

    # Get followers
    followers = my_client.get_followers(
        max_limit=2_500,
    )
    # Confirm matches direct pull from API
    n_followers = len(followers)
    print(f'Followers (from SDK): {n_followers}')
    my_info = get_profile_info(my_client.username)
    print(f'Followers (from API) {my_info.get("followersCount")}')

    # for follower in followers:
    #     name = follower.get('display_name')
    #     handle = follower.get('handle')
    #     description = follower.get('description', '')
    #     print(f'{name}\n\t{handle}\n\t{description}\n')

    df = get_dataframe(followers)
    plot_profiles(df)
    plot_profiles(df, kind='cdf')