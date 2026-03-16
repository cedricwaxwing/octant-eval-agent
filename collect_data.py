"""
Octant Data Collector
Pulls all historical epoch data from the Octant production API
and saves it as a single JSON file for your agent to query.

Usage:
    python collect_octant_data.py

Output:
    octant_data.json - complete dataset
"""

import json
import urllib.request
import urllib.error
import time
import sys

BASE_URL = "https://backend.mainnet.octant.app"

def fetch(path):
    """Fetch JSON from Octant API"""
    url = f"{BASE_URL}{path}"
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) OctantEvalAgent/1.0",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {path}")
        return None
    except Exception as e:
        print(f"  Error for {path}: {e}")
        return None


def main():
    print("=== Octant Data Collector ===\n")

    # Step 1: Get current epoch
    print("Fetching current epoch...")
    current = fetch("/epochs/current")
    if not current:
        print("Failed to get current epoch. Is the API up?")
        sys.exit(1)

    current_epoch = current["currentEpoch"]
    print(f"  Current epoch: {current_epoch}\n")

    dataset = {
        "meta": {
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "current_epoch": current_epoch,
            "api_base": BASE_URL,
        },
        "epochs": {},
    }

    # Step 2: For each finalized epoch, pull everything
    # Epochs 1 through (current - 1) should be finalized
    # Epoch 0 was a special pre-launch epoch
    for epoch_num in range(1, current_epoch):
        print(f"--- Epoch {epoch_num} ---")
        epoch_data = {}

        # Epoch stats (the big one: staking proceeds, rewards, matched, etc.)
        print(f"  Fetching epoch stats...")
        stats = fetch(f"/epochs/info/{epoch_num}")
        if stats:
            epoch_data["stats"] = stats
            print(f"    Total rewards: {stats.get('totalRewards', 'N/A')}")
            print(f"    Matched rewards: {stats.get('matchedRewards', 'N/A')}")

        # Project rewards for this epoch
        print(f"  Fetching project rewards...")
        rewards = fetch(f"/rewards/projects/epoch/{epoch_num}")
        if rewards:
            epoch_data["project_rewards"] = rewards.get("rewards", [])
            print(f"    {len(epoch_data['project_rewards'])} projects with rewards")

        # Project metadata (addresses + IPFS CID)
        print(f"  Fetching project metadata...")
        meta = fetch(f"/projects/epoch/{epoch_num}")
        if meta:
            epoch_data["project_addresses"] = meta.get("projectsAddresses", [])
            epoch_data["projects_cid"] = meta.get("projectsCid", "")
            print(f"    {len(epoch_data['project_addresses'])} projects listed")

        # Leverage
        print(f"  Fetching leverage...")
        leverage = fetch(f"/rewards/leverage/{epoch_num}")
        if leverage:
            epoch_data["leverage"] = leverage.get("leverage")
            print(f"    Leverage: {epoch_data['leverage']}")

        # Threshold
        print(f"  Fetching threshold...")
        threshold = fetch(f"/rewards/threshold/{epoch_num}")
        if threshold:
            epoch_data["threshold"] = threshold.get("threshold")

        # Donors
        print(f"  Fetching donors...")
        donors = fetch(f"/allocations/donors/{epoch_num}")
        if donors:
            epoch_data["donor_count"] = len(donors.get("donors", []))
            epoch_data["donors"] = donors.get("donors", [])
            print(f"    {epoch_data['donor_count']} donors")

        # Patrons
        print(f"  Fetching patrons...")
        patrons = fetch(f"/user/patrons/{epoch_num}")
        if patrons:
            epoch_data["patron_count"] = len(patrons.get("patrons", []))
            epoch_data["patrons"] = patrons.get("patrons", [])
            print(f"    {epoch_data['patron_count']} patrons")

        # Unused rewards
        print(f"  Fetching unused rewards...")
        unused = fetch(f"/rewards/unused/{epoch_num}")
        if unused:
            epoch_data["unused_rewards"] = unused.get("value")
            epoch_data["inactive_users"] = len(unused.get("addresses", []))
            print(f"    {epoch_data['inactive_users']} inactive users")

        # Allocations (all donor->project pairs)
        print(f"  Fetching allocations...")
        allocs = fetch(f"/allocations/epoch/{epoch_num}")
        if allocs:
            epoch_data["allocations"] = allocs.get("allocations", [])
            print(f"    {len(epoch_data['allocations'])} allocations")

        # Rewards rate
        print(f"  Fetching rewards rate...")
        rate = fetch(f"/epochs/rewards-rate/{epoch_num}")
        if rate:
            epoch_data["rewards_rate"] = rate.get("rewardsRate")

        dataset["epochs"][str(epoch_num)] = epoch_data
        print()
        time.sleep(0.5)  # be nice to their API

    # Step 3: Get project details across all epochs
    print("Fetching project details across all epochs...")
    epoch_list = ",".join(str(i) for i in range(1, current_epoch))
    details = fetch(f"/projects/details?epochs={epoch_list}&searchPhrases=")
    if details:
        dataset["all_projects"] = details.get("projectsDetails", [])
        print(f"  {len(dataset['all_projects'])} total project entries")

    # Save
    output_file = "octant_data.json"
    with open(output_file, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"\n=== Done! Saved to {output_file} ===")
    print(f"File size: {round(len(json.dumps(dataset)) / 1024, 1)} KB")


if __name__ == "__main__":
    main()