"""
🎲 AlgoDices, let's roll verifiable random dices on Algornd!

Usage:
  algodices.py optin
  algodices.py book <future_rounds>
  algodices.py roll <faces>

Commands:
  optin    Subscribe to AlgoDices.
  book     Book a die roll in future round.
  roll     Roll a die.

Options:
  -h, --help
"""

import sys
from docopt import docopt
from getpass import getpass

from algosdk import account
from algosdk import mnemonic
from algosdk.atomic_transaction_composer import AccountTransactionSigner
from algosdk.constants import MIN_TXN_FEE

from beaker.client import ApplicationClient, Network
from beaker.client.api_providers import AlgoExplorer

from algodices_dapp import AlgoDices

ALGO_DICES_APP_ID = 120974808


def args_types(args: dict) -> dict:
    if args["<future_rounds>"] is not None:
        args["<future_rounds>"] = int(args["<future_rounds>"])
    if args["<faces>"] is not None:
        args["<faces>"] = int(args["<faces>"])
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
        assert len(mnemonic_phrase.split()) == 25
    except AssertionError:
        quit('\n⚠️ Enter mnemonic phrase, formatted as: "word_1 ... word_25"')
    user = AccountTransactionSigner(mnemonic.to_private_key(mnemonic_phrase))
    user_address = account.address_from_private_key(user.private_key)

    # API
    testnet = AlgoExplorer(Network.TestNet)

    # APP
    algo_dices = ApplicationClient(
        client=testnet.algod(),
        app=AlgoDices(),
        app_id=ALGO_DICES_APP_ID,
        signer=user,
        sender=user_address,
    )

    # CLI
    if args["optin"]:
        print("\n --- Opt-in 🎲 AlgoDices App...")
        return algo_dices.opt_in()

    if args["book"]:
        current_round = testnet.algod().status()["last-round"]
        booked_round = current_round + args["<future_rounds>"]
        reveal_round = booked_round + 8
        print(f"\n --- 🔖 Booking a die roll for round {booked_round}...")
        algo_dices.call(
            method=AlgoDices.book_die_roll,
            future_round=booked_round,
        )
        return print(f" --- Result can be revealed from round: {reveal_round}")

    elif args["roll"]:
        current_round = testnet.algod().status()["last-round"]
        booked_round = algo_dices.get_account_state(user_address)["commitment_round"]
        rounds_left = booked_round + 8 - current_round
        if rounds_left > 0:
            print(f" --- ⏳ {rounds_left} round left to reveal die's roll...")
        else:
            sp = testnet.algod().suggested_params()
            sp.fee = 2 * MIN_TXN_FEE
            faces = args["<faces>"]
            result = algo_dices.call(
                suggested_params=sp,
                method=AlgoDices.roll_die,
                randomness_beacon=AlgoDices.beacon_app_id.default.value,
                faces=faces,
            )
            booked_round = result.return_value[0]
            faces = result.return_value[1]
            roll_result = result.return_value[2]
            return print(
                f" --- 🎲 d{faces} rolled at round {booked_round}: {roll_result}"
            )

    else:
        return print("\n --- Wrong command. Enter --help for CLI usage!\n")


if __name__ == "__main__":
    main()
