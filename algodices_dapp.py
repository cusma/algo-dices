"""
🎲 AlgoDices
"""

from typing import Final
from algosdk.constants import MIN_TXN_FEE
from pyteal import *
from beaker import *

MAX_N_DICES = 14
OP_CODE_BUDGET_TXNS = 1
TESTNET_BEACON_APP_ID = 110096026
MAINNET_BEACON_APP_ID = 947957720


class AlgoDices(Application):
    """AlgoDices Application"""

    ################
    # GLOBAL STATE #
    ################
    beacon_app_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        static=True,
        descr="The App ID of the Randomness Beacon. Must adhere to ARC-21.",
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

    @internal(TealType.uint64)
    def is_valid_faces(self, faces: Expr) -> Expr:
        return Or(
            faces == Int(2),
            faces == Int(4),
            faces == Int(6),
            faces == Int(8),
            faces == Int(10),
            faces == Int(12),
            faces == Int(20),
        )

    ###############
    # ABI METHODS #
    ###############
    @external
    def book_dices_roll(self, future_round: abi.Uint64) -> Expr:
        """
        Book dices roll for a future round.

        Args:
            future_round: Future round booked for dices roll
        """
        return Seq(
            # Preconditions
            Assert(
                future_round.get() > Global.round(),
                comment="Dices roll round must be in the future.",
            ),
            # Effects
            self.randomness_round[Txn.sender()].set(future_round.get()),
        )

    @external
    def roll_dices(
        self,
        randomness_beacon: abi.Application,
        dices: abi.DynamicArray[abi.Uint8],
        *,
        output: abi.DynamicArray[abi.Uint8],
    ) -> Expr:
        """
        Roll dices with a given number of faces. Fee: 3 * min_fee.

        Example:
            - Roll 1d6, set: dices = [6]
            - Roll 2d6, 1d8 and 1d20, set: dices = [6, 6, 8, 20]

        Args:
            randomness_beacon: Randomness Beacon App ID (TestNet: 110096026, MainNet: 947957720)
            dices: Array of dices to roll (faces: 2, 4, 6, 8, 10, 12, 20)

        Returns:
            Dices roll result.
        """
        # Scratch Space
        i = ScratchVar(TealType.uint64)
        dice = ScratchVar(TealType.uint64)
        p_dice = ScratchVar(TealType.uint64)
        p_dice_bytes = ScratchVar(TealType.bytes)
        rolled_dices = ScratchVar(TealType.uint64)
        dices_results_bytes = ScratchVar(TealType.bytes)
        dices_results = abi.make(abi.DynamicArray[abi.Uint8])

        n_dices = dices.length()
        get_dice = dice.store(dices[i.load()].use(lambda value: value.get()))
        roll_dice = ((p_dice.load() / rolled_dices.load()) % dice.load()) + Int(1)
        randomness = self.get_randomness()

        idx = i.store(Int(0))
        idx_cond = i.load() < n_dices
        idx_iter = i.store(i.load() + Int(1))

        op_code_budget = OpUp(mode=OpUpMode.OnCall)
        return Seq(
            op_code_budget.maximize_budget(
                fee=Int(OP_CODE_BUDGET_TXNS * MIN_TXN_FEE),
                fee_source=OpUpFeeSource.GroupCredit,
            ),
            # Preconditions
            Assert(
                randomness_beacon.application_id() == self.beacon_app_id,
                comment="Wrong Randomness Beacon App ID.",
            ),
            Assert(
                n_dices <= Int(MAX_N_DICES),
                comment=f"Too many dices. Max dices per roll: {MAX_N_DICES}.",
            ),
            # Effects
            p_dice.store(Int(1)),
            For(idx, idx_cond, idx_iter).Do(
                get_dice,
                Assert(
                    self.is_valid_faces(dice.load()),
                    comment="Number of faces must be equal to real ideal dices.",
                ),
                p_dice.store(p_dice.load() * dice.load()),
            ),
            p_dice_bytes.store(Itob(p_dice.load())),
            p_dice_bytes.store(BytesMod(randomness, p_dice_bytes.load())),
            p_dice.store(Btoi(p_dice_bytes.load())),
            rolled_dices.store(Int(1)),
            (n_results := abi.Uint16()).set(n_dices),
            dices_results_bytes.store(n_results.encode()),
            For(idx, idx_cond, idx_iter).Do(
                get_dice,
                (result := abi.Uint8()).set(roll_dice),
                dices_results_bytes.store(
                    Concat(dices_results_bytes.load(), result.encode())
                ),
                rolled_dices.store(rolled_dices.load() * dice.load()),
            ),
            self.randomness_round[Txn.sender()].set_default(),
            dices_results.decode(dices_results_bytes.load()),
            output.set(dices_results),
        )

    ##################
    # DAPP LIFECYCLE #
    ##################
    @create
    def create(self, randomness_beacon: abi.Application) -> Expr:
        """
        AlgoDices App Create

        Args:
            randomness_beacon: Randomness Beacon App ID (TestNet: 110096026, MainNet: 947957720)
        """
        return Seq(
            Assert(
                Txn.global_num_uints() == Int(self.app_state.num_uints),
                comment="Wrong Global State Schema. Must be: 1 uint.",
            ),
            Assert(
                Txn.global_num_byte_slices() == Int(self.app_state.num_byte_slices),
                comment="Wrong Global State Schema. Must be: 0 byte slices.",
            ),
            Assert(
                Txn.local_num_uints() == Int(self.app_state.num_uints),
                comment="Wrong Local State Schema. Must be: 1 uint.",
            ),
            Assert(
                Txn.local_num_byte_slices() == Int(self.app_state.num_byte_slices),
                comment="Wrong Local State Schema. Must be: 0 byte slices.",
            ),
            Assert(
                Not(self.beacon_app_id.exists()),
                comment="AlgoDices App already created!",
            ),
            Assert(
                Or(
                    randomness_beacon.application_id() == Int(TESTNET_BEACON_APP_ID),
                    randomness_beacon.application_id() == Int(MAINNET_BEACON_APP_ID),
                ),
                comment="Wrong Randomness Beacon App ID. Must be either: "
                "110096026 (TestNet) or 947957720 (MainNet).",
            ),
            self.beacon_app_id.set(randomness_beacon.application_id()),
        )

    @opt_in
    def opt_in(self) -> Expr:
        """
        AlgoDices App Opt-In
        """
        return self.initialize_account_state()


if __name__ == "__main__":
    AlgoDices().dump("./artifacts")
