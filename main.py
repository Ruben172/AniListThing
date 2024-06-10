import httpx

al_url = "https://graphql.anilist.co"
al_query = '''
    query ($id: Int, $page: Int, $perPage: Int, $userName: String) {
        Page(page: $page, perPage: $perPage) {
            pageInfo {
                hasNextPage
            }
            mediaList(userName: $userName, type: ANIME, id: $id) {
                status
                media {
                    title {
                        romaji
                    }
                    idMal
                    status
                }
            }
        }
    }
'''
mal_base_url = "https://api.myanimelist.net/v2/users/"
mal_headers = {
    "X-MAL-CLIENT-ID": "MAL_CLIENT_ID_HERE"
}


def request_with_retries(method: str, url: str, json: dict, headers: dict, max_attempts: int) -> httpx.Response:
    res = httpx.request(method=method, url=url, json=json, headers=headers)
    attempts = 1
    while res.status_code != 200:
        print(f"Retrying {url} (Received {res.status_code})")
        res = httpx.request(method=method, url=url, json=json, headers=headers)
        attempts += 1
        if attempts > max_attempts:
            print(f"Giving up on {url}, too many attempts.")
            return res
    return res


def parse_anilist(user: str) -> dict:
    user_planning = set()
    user_not_planning = set()
    variables = {
        "userName": user,
        "page": 1
    }
    has_next_page = True
    while has_next_page:
        res = request_with_retries("POST", al_url, {'query': al_query, 'variables': variables}, None, 3)
        if res.status_code != 200:
            print("Request failed.")
            exit(0)
        res_json = res.json()["data"]["Page"]
        has_next_page = res_json["pageInfo"]["hasNextPage"]
        variables["page"] += 1
        for media_item in res_json["mediaList"]:
            if media_item["media"]["status"] == "NOT_YET_RELEASED":
                continue
            mal_id = media_item["media"]["idMal"]
            if mal_id not in show_id_name.keys():
                show_id_name[mal_id] = media_item["media"]["title"]["romaji"]
            if media_item["status"] == "PLANNING":
                user_planning.add(mal_id)
            else:
                user_not_planning.add(mal_id)
    return {
        "planning": user_planning,
        "not_planning": user_not_planning
    }


def parse_myanimelist(user: str) -> dict:
    user_planning = set()
    user_not_planning = set()
    has_next_page = True
    url = mal_base_url + user + "/animelist?limit=1000&fields=list_status,status"
    while has_next_page:
        res = request_with_retries("GET", url, None, mal_headers, 3)
        if res.status_code != 200:
            print("Request failed.")
            exit(0)
        res_json = res.json()
        if "next" in res_json["paging"].keys():
            url = res_json["paging"]["next"]
        else:
            has_next_page = False
        for media_item in res_json["data"]:
            if media_item["node"]["status"] == "not_yet_aired":
                continue
            mal_id = media_item["node"]["id"]
            if mal_id not in show_id_name.keys():
                show_id_name[mal_id] = media_item["node"]["title"]
            if media_item["list_status"]["status"] == "plan_to_watch":
                user_planning.add(mal_id)
            else:
                user_not_planning.add(mal_id)
    return {
        "planning": user_planning,
        "not_planning": user_not_planning
    }


if __name__ == '__main__':
    anilist_users = input("Enter AniList users (space separated)\n> ").split(" ")
    mal_users = input("Enter MAL users (space separated)\n> ").split(" ")
    anime_lists = {}
    show_id_name = {}
    for al_user in anilist_users:
        if al_user == "":
            continue
        print(f"Fetching list of {al_user}@AL")
        anime_lists[f"{al_user}@AL"] = parse_anilist(al_user)
    for mal_user in mal_users:
        if mal_user == "":
            continue
        print(f"Fetching list of {mal_user}@MAL")
        anime_lists[f"{mal_user}@MAL"] = parse_myanimelist(mal_user)

    total_planning = set()
    total_not_planning = set()
    for ani_list in anime_lists.keys():
        total_planning = total_planning.union(anime_lists[ani_list]["planning"])
        total_not_planning = total_not_planning.union(anime_lists[ani_list]["not_planning"])
    possible_shows = total_planning.difference(total_not_planning)

    possible_shows_groups = {}
    for show in possible_shows:
        name = show_id_name[show]
        planning_users = []
        for user in anime_lists:
            if show in anime_lists[user]["planning"]:
                planning_users.append(user)
        planning_users_string = ", ".join(planning_users)
        if planning_users_string not in possible_shows_groups.keys():
            possible_shows_groups[planning_users_string] = []
        possible_shows_groups[planning_users_string].append(name)

    print("\n" * 5)
    for group in possible_shows_groups.keys():
        sorted_shows = sorted(possible_shows_groups[group])
        print(f"\n{group}:")
        for show in sorted_shows:
            print(show)
