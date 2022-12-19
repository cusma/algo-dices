"""
🎲 AlgoDices, let's roll verifiable random dices on Algornd!

Usage:
  algodices.py optin [--test]
  algodices.py book <future_rounds> [--test]
  algodices.py roll <dice> ... [--test]

Commands:
  optin    Subscribe to AlgoDices.
  book     Book a die roll in future round.
  roll     Roll dices (e.g. 2d6, 1d8 and 1d20: roll 6 6 8 20).

Options:
  -h, --help
  -t, --test
"""

import sys
from docopt import docopt
from getpass import getpass

from algosdk import account
from algosdk import mnemonic
from algosdk.atomic_transaction_composer import AccountTransactionSigner
from algosdk.constants import MIN_TXN_FEE, MNEMONIC_LEN

from beaker.client import ApplicationClient, Network
from beaker.client.api_providers import AlgoExplorer
from beaker.client.logic_error import LogicException

from algodices_dapp import (
    MAINNET_BEACON_APP_ID,
    MAX_N_DICES,
    OP_CODE_BUDGET_TXNS,
    TESTNET_BEACON_APP_ID,
    AlgoDices,
)

TESTNET_ALGO_DICES_APP_ID = 149459287
MAINNET_ALGO_DICES_APP_ID = 0  # TODO

RANDOMNESS_BEACON_DELAY = 8
FACES = [2, 4, 6, 8, 10, 12, 20]


def args_types(args: dict) -> dict:
    if args["<future_rounds>"] is not None:
        args["<future_rounds>"] = int(args["<future_rounds>"])
    if args["<dice>"] is not None:
        args["<dice>"] = list(map(int, args["<dice>"]))
    return args


def main():
    if len(sys.argv) == 1:
        # Display help if no arguments, see:
        # https://github.com/docopt/docopt/issues/420#issuecomment-405018014
        sys.argv.append("--help")

    args = args_types(docopt(__doc__))

    # USER
    mnemonic_phrase = getpass(prompt="Mnemonic (word_1 word_2 ... word_25):")
    try:
        assert len(mnemonic_phrase.split()) == MNEMONIC_LEN
    except AssertionError:
        quit('\n⚠️ Enter mnemonic phrase, formatted as: "word_1 ... word_25"')
    user = AccountTransactionSigner(mnemonic.to_private_key(mnemonic_phrase))
    user_address = account.address_from_private_key(user.private_key)

    if args["--test"]:
        network = Network.TestNet
        beacon_app_id = TESTNET_BEACON_APP_ID
        algo_dices_app_id = TESTNET_ALGO_DICES_APP_ID
    else:
        network = Network.MainNet
        beacon_app_id = MAINNET_BEACON_APP_ID
        algo_dices_app_id = TESTNET_ALGO_DICES_APP_ID

    # API
    api = AlgoExplorer(network)

    # APP CLIENT
    algo_dices = ApplicationClient(
        client=api.algod(),
        app=AlgoDices(),
        app_id=algo_dices_app_id,
        signer=user,
        sender=user_address,
    )
    algo_dices.build()

    # CLI
    if args["optin"]:
        print("\n --- Opt-in 🎲 AlgoDices App...")
        try:
            algo_dices.opt_in()
        except LogicException as e:
            print(f"\n{e}\n")
        return

    if args["book"]:
        current_round = api.algod().status()["last-round"]
        booked_round = current_round + args["<future_rounds>"]
        reveal_round = booked_round + RANDOMNESS_BEACON_DELAY
        print(f"\n --- 🔖 Booking a dices roll for round {booked_round}...")
        try:
            algo_dices.call(
                method=AlgoDices.book_dices_roll,
                future_round=booked_round,
            )
            print(f" --- Result can be revealed from round: {reveal_round}")
        except LogicException as e:
            print(f"\n{e}\n")
        return

    elif args["roll"]:
        dices = args["<dice>"]
        if len(dices) > MAX_N_DICES:
            quit(f"\n⚠️ Too many dices. Max {MAX_N_DICES} dices per roll!")
        if not all(faces in FACES for faces in args["<dice>"]):
            quit(f"\n⚠️ Number of faces must be either: {FACES}")

        current_round = api.algod().status()["last-round"]
        booked_round = algo_dices.get_account_state(user_address)["randomness_round"]
        rounds_left = booked_round + RANDOMNESS_BEACON_DELAY - current_round
        if rounds_left > 0:
            print(f" --- ⏳ {rounds_left} round left to reveal dices roll...")
        else:
            sp = api.algod().suggested_params()
            sp.fee = (2 + OP_CODE_BUDGET_TXNS) * MIN_TXN_FEE
            try:
                results = algo_dices.call(
                    suggested_params=sp,
                    method=AlgoDices.roll_dices,
                    randomness_beacon=beacon_app_id,
                    dices=args["<dice>"],
                )
                print("\n --- 🎰 RESULTS 🎰")
                for i in range(len(dices)):
                    print(f" --- 🎲 d{dices[i]}:\t{results.return_value[i]}")
            except LogicException as e:
                print(f"\n{e}\n")
            return

    else:
        return print("\n --- Wrong command. Enter --help for CLI usage!\n")


if __name__ == "__main__":
    main()
