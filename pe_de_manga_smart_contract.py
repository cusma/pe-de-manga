"""
Algorand Smart Contract Pe de Manga: rega, diga oxê e receba sua manga NFT! 🥭
"""

from algosdk.future.transaction import StateSchema
from pyteal import (
    And,
    App,
    Approve,
    Assert,
    Bytes,
    Cond,
    Expr,
    Global,
    If,
    InnerTxn,
    InnerTxnBuilder,
    Int,
    Mode,
    OnComplete,
    Reject,
    Seq,
    Txn,
    TxnField,
    TxnType,
    compileTeal,
)

TEAL_VERSION = 5

# SMART CONTRACT STATE SCHEMA
GLOBAL_NA_MANGUEIRA = Bytes("naMangueira")

GLOBAL_STATE = StateSchema(num_uints=1, num_byte_slices=0)
LOCAL_STATE = StateSchema(num_uints=0, num_byte_slices=0)

# SMART CONTRACT METHODS
METHOD_REGA = "rega"
METHOD_COLHE = "oxê"


def pe_de_manga_approval() -> Expr:
    return Cond(
        [Txn.application_id() == Int(0), on_app_create()],
        [Txn.on_completion() == OnComplete.NoOp, on_app_call()],
    )


def pe_de_manga_clear() -> Expr:
    return Reject()


def on_app_create() -> Expr:
    precondition = And(
        Txn.global_num_uints() == Int(GLOBAL_STATE.num_uints),
        Txn.global_num_byte_slices() == Int(GLOBAL_STATE.num_byte_slices),
        Txn.local_num_uints() == Int(LOCAL_STATE.num_uints),
        Txn.local_num_byte_slices() == Int(LOCAL_STATE.num_byte_slices),
    )

    return Seq(
        Assert(precondition),
        App.globalPut(GLOBAL_NA_MANGUEIRA, Int(0)),
        Approve()
    )


def on_app_call() -> Expr:
    method_selector = Txn.application_args[0]

    return Seq(
        Assert(Txn.application_args.length() == Int(1)),
        Cond(
            [method_selector == Bytes(METHOD_REGA), rega_pe_de_manga()],
            [method_selector == Bytes(METHOD_COLHE), colhe_manga()],
        ),
        Approve(),
    )


def rega_pe_de_manga() -> Expr:
    mangueira_account = Global.current_application_address()

    nao_tem_manga = App.globalGet(GLOBAL_NA_MANGUEIRA) == Int(0)

    nasce_manga = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_name: Bytes("MANGA"),
                TxnField.config_asset_unit_name: Bytes("🥭"),
                TxnField.config_asset_url: Bytes(
                    "ipfs://bafkreibojeqclpzpz73gotdzqtondllgkncdzarmpad3i5alcvhodv7ujy#arc3"
                ),
                TxnField.config_asset_metadata_hash: Bytes(
                    "LkkgJb8vz/ZnTHmE3NGtZlNEPIIseAe0dAsVTuHX9E4="
                ),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_total: Int(1),
                TxnField.config_asset_manager: mangueira_account,
                TxnField.config_asset_clawback: Global.zero_address(),
                TxnField.config_asset_freeze: Global.zero_address(),
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),  # cria uma manga como non-fungible token
        App.globalPut(GLOBAL_NA_MANGUEIRA, InnerTxn.created_asset_id()),
        # guarda o Asset ID da ultima manga criada na mangueira
        Approve(),
    )

    return Seq(
        If(nao_tem_manga).Then(
            nasce_manga
        ).Else(
            Reject()
        )
    )


def colhe_manga() -> Expr:
    manga = App.globalGet(GLOBAL_NA_MANGUEIRA)

    colher_da_mangueira = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: manga,
                TxnField.asset_amount: Int(1),
                TxnField.asset_receiver: Txn.sender(),  # quem chamou a dApp
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),  # envie o token MANGA pra quem disse oxê
        App.globalPut(GLOBAL_NA_MANGUEIRA, Int(0)),
        # cancelar o Asset ID da manga que foi tirada da mangueira
        Approve(),
    )

    return colher_da_mangueira


def compile_stateful(program) -> str:
    return compileTeal(
        program, Mode.Application, assembleConstants=True, version=TEAL_VERSION
    )


if __name__ == "__main__":
    print(compile_stateful(pe_de_manga_approval()))
