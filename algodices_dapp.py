"""
🎲 AlgoDices
"""

from typing import Final, Literal
from pyteal import *
from beaker import *


class AlgoDices(Application):
    """Algorand Dices Application"""

    ################
    # GLOBAL STATE #
    ################
    beacon_app_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(110096026),
        static=True,
        descr="The App ID of the randomness beacon. Must adhere to ARC-21.",
    )

    ################
    # LOCAL  STATE #
    ################
    randomness_round: Final[AccountStateValue] = AccountStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="The round this account committed to, for future randomness.",
    )

    ###############
    # SUBROUTINES #
    ###############
    @internal(TealType.bytes)
    def get_randomness(self) -> Expr:
        """Requests randomness from random oracle beacon for given round."""
        return Seq(
            # Prep method call arguments
            (req_round := abi.Uint64()).set(self.randomness_round[Txn.sender()]),
            (user_data := abi.DynamicBytes()).set(Txn.sender()),
            # Get randomness from oracle
            InnerTxnBuilder.ExecuteMethodCall(
                app_id=self.beacon_app_id,
                method_signature="must_get(uint64,byte[])byte[]",
                args=[req_round, user_data],
                extra_fields={TxnField.fee: Int(0)},
            ),
            # Remove first 4 bytes (ABI return prefix) and return the rest
            Suffix(InnerTxn.last_log(), Int(4)),
        )

    ###############
    # ABI METHODS #
    ###############
    @external
    def book_die_roll(self, future_round: abi.Uint64) -> Expr:
        """
        Book a die roll for a future round.

        Args:
            future_round: Future round booked for a die roll
        """
        return Seq(
            Assert(
                future_round.get() > Global.round(),
                comment="Die roll round must be in the future.",
            ),
            self.randomness_round[Txn.sender()].set(future_round.get()),
        )

    @external
    def roll_die(
        self,
        randomness_beacon: abi.Application,
        faces: abi.Uint64,
        *,
        output: abi.StaticArray[abi.Uint64, Literal[3]],
    ) -> Expr:
        """
        Roll a die with a given number of faces.

        Args:
            randomness_beacon: Randomness Beacon App ID (110096026)
            faces: Number of faces (e.g. 2, 4, 6, 8, 10, 12, 20, 100, ...)

        Returns:
            Die roll: (booked_round, faces, result)
        """
        randomness = Btoi(
            Extract(string=self.get_randomness(), start=Int(0), length=Int(8))
        )
        return Seq(
            Assert(
                randomness_beacon.application_id() == self.beacon_app_id,
                comment="Randomness Beacon App ID must be correct.",
            ),
            (booked_round := abi.Uint64()).set(self.randomness_round[Txn.sender()]),
            (result := abi.Uint64()).set(randomness % faces.get() + Int(1)),
            self.randomness_round[Txn.sender()].set_default(),
            output.set([booked_round, faces, result]),
        )

    ##################
    # DAPP LIFECYCLE #
    ##################
    @create
    def create(self) -> Expr:
        """
        AlgoDices App Create
        """
        return self.initialize_application_state()

    @opt_in
    def opt_in(self) -> Expr:
        """
        AlgoDices App Opt-In
        """
        return self.initialize_account_state()


if __name__ == "__main__":
    AlgoDices().dump("./artifacts")
