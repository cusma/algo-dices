🎲 AlgoDices
------------
Let's roll your dices on Algorand!

## Overview
[AlgoDices](https://testnet.algoexplorer.io/application/121287966) application
let players **roll dices on-chain** (TestNet), thanks the [*Randomness Beacon Application*](https://developer.algorand.org/articles/usage-and-best-practices-for-randomness-beacon/).

Starting from AVM 7, Algorand enables [turstless randomness on chain](https://developer.algorand.org/articles/randomness-on-algorand),
thanks to the use of [VRF](https://en.wikipedia.org/wiki/Verifiable_random_function):
with the `vrf_verify` opcode an oracle Smart Contract can prove that a
*pseudo-random value* has been honestly computed off-chain through a VRF process
for a given blockchain round in the future.

AlgoDices makes use of the Randomness Beacon App [110096026](https://testnet.algoexplorer.io/application/110096026)
deployed on TestNet, which verifies, stores and provides the randomness to
other applications for a given (future) round according to [ARC-21](https://arc.algorand.foundation/ARCs/arc-0021).

## ABI
AlgoDices ABI exposes two methods:

1. `book_die_roll`
2. `roll_die`

AlgoDices App requires players to opt-in.

### Book a (future) die roll
Players can book a die roll for a future round, committing to future
randomness:

```json
{
    "name": "book_die_roll",
    "args": [
        {
            "type": "uint64",
            "name": "future_round",
            "desc": "Future round booked for a die roll"
        }
    ],
    "returns": {
        "type": "void"
    },
    "desc": "Book a die roll for a future round."
}
```

#### Future round committment
Althogh the more the round is distant in the future the better is for security,
AlgoDices App does not impose any minimum `future_round`, leaving this check to
the client. An external App interacting with AlgoDices, for example, could
mandate `future_round` to be greater than current round plus `N`.

⚠️ Calling `book_die_roll` twice will overwrite the last booked round, even if
the previous booked randomness is unused.

### Let's roll a die!
Once the booked randomness is available, players can roll a die with a *"real"
number of faces* (`d4`, `d6`, `d8`, `d10`, `d12`, `d20`, are common dices in
board games).

⚠️ Players should wait at least for `future_round + 8` round to be sure that
their booked randomness is available in the Randomness Beacon App.

```json
{
    "name": "roll_die",
    "args": [
        {
            "type": "application",
            "name": "randomness_beacon",
            "desc": "Randomness Beacon App ID (110096026)"
        },
        {
            "type": "uint64",
            "name": "faces",
            "desc": "Number of faces (2, 4, 6, 8, 10, 12, 20)"
        }
    ],
    "returns": {
        "type": "uint64[3]",
        "desc": "Die roll: (booked_round, faces, result)"
    },
    "desc": "Roll a die with a given number of faces."
}
```

AlgoDice `die_roll` returns an array containing:
1. Randomness booked round;
2. Die's faces;
3. The result.

## 🎰 Games
On-chain games can _call_ AlgoDices imposing their own rules, for example:
a `GameApp` calls `roll_die` two times (on behalf of players Alice and Bob
participating in the game thourgh proxy Contract Accounts controlled by
GameApp) as Inner Transactions executed in the same GameApp Call, requiring
`faces = 6`. The highest result wins the match.

## CLI
You can easily roll a die with the Python 🎲 AlgoDices CLI.

Clone `algo-dice` repo an open it:
```shell
$ git clone git@github.com:cusma/algo-dices.git
$ cd algo-dices
```

Install the virtual environment described in `Pipfile` using `pipenv`:
```shell
$ pipenv install
```

Lounch 🎲 AlgoDices CLI:
```shell
$ pipenv run python3 algodices.py

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
```

⚠️ AlgoDices is deployed on TestNet, players need a funded TestNet Account.

⚠️ AlgoDices CLI requires entering a mnemonic phrase formatted as:
`"word_1 ... word_25"`.

## Future developments (community welcome)
- [ ] Multiple dices rolls on single round (e.g. `[2d6, 1d8, 1d20]`);
- [ ] Contract Account proxy for players.

## Credits
Thanks to [@ori-shem-tov](https://github.com/ori-shem-tov),
[@fabrice102](https://github.com/fabrice102) for the Randomness Oracle
Application and [@barnjamin](https://github.com/barnjamin) for the
[CoinFilpper](https://github.com/algorand-devrel/coin-flipper) example that
inspired AlgoDices.
