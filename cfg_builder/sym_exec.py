import base64
import errno
import pickle
import signal
import time
import tokenize
import traceback
import zlib
from collections import namedtuple
from tokenize import NAME, NEWLINE, NUMBER

from numpy import mod
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich import box
from rich.console import Console

from cfg_builder.basicblock import BasicBlock
from cfg_builder.execution_states import EXCEPTION, PICKLE_PATH, UNKNOWN_INSTRUCTION
from cfg_builder.utils import *
from cfg_builder.vargenerator import *
from defect_identifier.defect import *
from defect_identifier.identifier import Identifier
from feature_detector.semantic_analysis import *
from feature_detector.sleepmint_analysis import *

# Initiate table for live print.
console = Console()
table = Table()
live = Live(table, console=console, vertical_overflow="crop", auto_refresh=True)

log = logging.getLogger(__name__)

# Store visited blocks
visited_blocks = set()

UNSIGNED_BOUND_NUMBER = 2**256 - 1
CONSTANT_ONES_159 = BitVecVal((1 << 160) - 1, 256)


def dynamic_defect_identification(g_src_map, global_problematic_pcs):
    """Find defects during execution

    Args:
        g_src_map (_type_): source map
        global_problematic_pcs (_type_): defects pcs

    Returns:
        defects: defects detection results during execution
    """
    public_burn = PublicBurnDefect(g_src_map, global_problematic_pcs["burn_defect"])
    unlimited_minting = UnlimitedMintingDefect(
        g_src_map, global_problematic_pcs["unlimited_minting_defect"]
    )
    proxy = RiskyProxyDefect(g_src_map, global_problematic_pcs["proxy_defect"])
    reentrancy = ReentrancyDefect(
        g_src_map, global_problematic_pcs["reentrancy_defect"]
    )
    violation = ViolationDefect(g_src_map, global_problematic_pcs["violation_defect"])
    return proxy, reentrancy, unlimited_minting, violation, public_burn

def generate_table(
    opcode, block_cov, pc, perc, g_src_map, global_problematic_pcs, current_func_name
) -> Table:

    """Make a new table for live presentation

    Returns:
        table: table for live show
    """
    defect_table = Table(box=box.SIMPLE)

    defect_table.add_column("Defect", justify="center", style="bold", no_wrap=True)

    defect_table.add_row("Privileged Address")
    defect_table.add_row("Unrestricted 'from'")
    defect_table.add_row("Owner Inconsistency")
    defect_table.add_row("Empty Transfer Event")

    end = time.time()

    time_coverage_table = Table(box=box.SIMPLE)
    time_coverage_table.add_column(
        "Time", justify="left", style="cyan", no_wrap=True, width=8
    )
    time_coverage_table.add_column(
        "Code Coverage", justify="left", style="yellow", no_wrap=True
    )
    time_coverage_table.add_column(
        "Block Coverage", justify="left", style="yellow", no_wrap=True
    )
    time_coverage_table.add_row(
        str(round(end - begin, 1)), str(round(perc, 1)), str(round(block_cov, 1))
    )

    block_table = Table(box=box.SIMPLE)
    block_table.add_column("PC", justify="left", style="cyan", no_wrap=True, width=8)
    block_table.add_column(
        "Opcode", justify="left", style="yellow", no_wrap=True, width=8
    )
    block_table.add_column(
        "Current Function", justify="left", style="yellow", no_wrap=True, min_width=19
    )

    block_table.add_row(str(pc), opcode, current_func_name)

    state_table = Table.grid(expand=True)
    state_table.add_column(justify="center")
    state_table.add_row(time_coverage_table)
    state_table.add_row(block_table)

    reporter = Table(box=box.ROUNDED, title="WakeMint GENESIS v0.0.1")
    reporter.add_column("Defect Detection", justify="center")
    reporter.add_column("Execution States", justify="center")
    reporter.add_row(defect_table, state_table)
    return reporter

# def generate_table(
#     opcode, block_cov, pc, perc, g_src_map, global_problematic_pcs, current_func_name
# ) -> Table:
#     (
#         proxy,
#         reentrancy,
#         unlimited_minting,
#         violation,
#         public_burn,
#     ) = dynamic_defect_identification(g_src_map, global_problematic_pcs)
#     """Make a new table for live presentation

#     Returns:
#         table: table for live show
#     """
#     defect_table = Table(box=box.SIMPLE)

#     defect_table.add_column("Defect", justify="right", style="bold", no_wrap=True)
#     defect_table.add_column("Status", style="green")
#     defect_table.add_column("Location", justify="left", style="cyan")

#     defect_table.add_row("Risky Mutable Proxy", str(proxy.is_defective()), str(proxy))
#     defect_table.add_row(
#         "ERC-721 Reentrancy", str(reentrancy.is_defective()), str(reentrancy)
#     )
#     defect_table.add_row(
#         "Unlimited Minting",
#         str(unlimited_minting.is_defective()),
#         str(unlimited_minting),
#     )
#     defect_table.add_row(
#         "Missing Requirements", str(violation.is_defective()), str(violation)
#     )
#     defect_table.add_row(
#         "Public Burn", str(public_burn.is_defective()), str(public_burn)
#     )
#     end = time.time()

#     time_coverage_table = Table(box=box.SIMPLE)
#     time_coverage_table.add_column(
#         "Time", justify="left", style="cyan", no_wrap=True, width=8
#     )
#     time_coverage_table.add_column(
#         "Code Coverage", justify="left", style="yellow", no_wrap=True
#     )
#     time_coverage_table.add_column(
#         "Block Coverage", justify="left", style="yellow", no_wrap=True
#     )
#     time_coverage_table.add_row(
#         str(round(end - begin, 1)), str(round(perc, 1)), str(round(block_cov, 1))
#     )

#     block_table = Table(box=box.SIMPLE)
#     block_table.add_column("PC", justify="left", style="cyan", no_wrap=True, width=8)
#     block_table.add_column(
#         "Opcode", justify="left", style="yellow", no_wrap=True, width=8
#     )
#     block_table.add_column(
#         "Current Function", justify="left", style="yellow", no_wrap=True, min_width=19
#     )

#     block_table.add_row(str(pc), opcode, current_func_name)

#     state_table = Table.grid(expand=True)
#     state_table.add_column(justify="center")
#     state_table.add_row(time_coverage_table)
#     state_table.add_row(block_table)

#     reporter = Table(box=box.ROUNDED, title="WakeMint GENESIS v0.0.1")
#     reporter.add_column("Defect Detection", justify="center")
#     reporter.add_column("Execution States", justify="center")
#     reporter.add_row(defect_table, state_table)
#     return reporter


class Parameter:
    def __init__(self, **kwargs):
        attr_defaults = {
            "stack": [],
            "calls": [],
            "memory": [],
            "visited": [],
            "overflow_pcs": [],
            "mem": {},
            "analysis": {},
            "sha3_list": {},
            "global_state": {},
            "path_conditions_and_vars": {},
        }
        for attr, default in six.iteritems(attr_defaults):
            setattr(self, attr, kwargs.get(attr, default))

    def copy(self):
        _kwargs = custom_deepcopy(self.__dict__)
        return Parameter(**_kwargs)


def initGlobalVars():
    # Initialize global variables
    global g_src_map
    global solver
    # Z3 solver
    solver = Solver()
    solver.set("timeout", global_params.TIMEOUT)

    global MSIZE
    MSIZE = False

    global revertible_overflow_pcs
    revertible_overflow_pcs = set()

    global g_disasm_file
    with open(g_disasm_file, "r") as f:
        disasm = f.read()
    if "MSIZE" in disasm:
        MSIZE = True

    global g_timeout
    g_timeout = False

    global visited_pcs
    visited_pcs = set()

    global results
    if g_src_map:
        global start_block_to_func_sig
        start_block_to_func_sig = {}

        results = {
            "evm_code_coverage": "",
            "instructions": "",
            "time": "",
            "analysis": {
                "privileged_address": [],
                "unrestricted_from_and_owner_inconsistency": [],
                "empty_transfer_event": [],
            },
            "bool_defect": {
                "privileged_address": False,
                "unrestricted_from_and_owner_inconsistency": False,
                "empty_transfer_event": False
            },
        }
    else:
        results = {
            "evm_code_coverage": "",
            "instructions": "",
            "time": "",
            "bool_defect": {
                "privileged_address": False,
                "unrestricted_from_and_owner_inconsistency": False,
                "empty_transfer_event": False
            },
        }

    global calls_affect_state
    calls_affect_state = {}

    # capturing the last statement of each basic block
    global end_ins_dict
    end_ins_dict = {}

    # capturing all the instructions, keys are corresponding addresses
    global instructions
    instructions = {}

    # capturing the "jump type" of each basic block
    global jump_type
    jump_type = {}

    global vertices
    vertices = {}

    global edges
    edges = {}

    # start: end
    global blocks
    blocks = {}

    global visited_edges
    visited_edges = {}

    global money_flow_all_paths
    money_flow_all_paths = []

    global reentrancy_all_paths
    reentrancy_all_paths = []

    # store the path condition corresponding to each path in money_flow_all_paths
    global path_conditions
    path_conditions = []

    global global_problematic_pcs  # for different defects
    global_problematic_pcs = {
        "privileged_address": [],
        "unrestricted_from_and_owner_inconsistency": [],
        "empty_transfer_event": [],
    }
    # global_problematic_pcs = {
    #     "proxy_defect": [],
    #     "burn_defect": [],
    #     "reentrancy_defect": [],
    #     "unlimited_minting_defect": [],
    #     "violation_defect": [],
    # }

    # store global variables, e.g. storage, balance of all paths
    global all_gs
    all_gs = []

    global total_no_of_paths
    total_no_of_paths = 0

    global no_of_test_cases
    no_of_test_cases = 0

    # to generate names for symbolic variables
    global gen
    gen = Generator()

    global rfile
    if global_params.REPORT_MODE:
        rfile = open(g_disasm_file + ".report", "w")


def is_testing_evm():
    return global_params.UNIT_TEST != 0


def compare_storage_and_gas_unit_test(global_state, analysis):
    unit_test = pickle.load(open(PICKLE_PATH, "rb"))
    test_status = unit_test.compare_with_symExec_result(global_state, analysis)
    exit(test_status)


def change_format():
    """Change format for tokenization and buildng CFG"""
    with open(g_disasm_file) as disasm_file:
        file_contents = disasm_file.readlines()
        i = 0
        firstLine = file_contents[0].strip("\n")
        for line in file_contents:
            line = line.replace(":", "")
            lineParts = line.split(" ")
            try:  # removing initial zeroes
                lineParts[0] = str(int(lineParts[0], 16))

            except:
                lineParts[0] = lineParts[0]
            lineParts[-1] = lineParts[-1].strip("\n")
            try:  # adding arrow if last is a number
                lastInt = lineParts[-1]
                if (int(lastInt, 16) or int(lastInt, 16) == 0) and len(lineParts) > 2:
                    lineParts[-1] = "=>"
                    lineParts.append(lastInt)
            except Exception:
                pass
            file_contents[i] = " ".join(lineParts)
            i = i + 1
        file_contents[0] = firstLine
        file_contents[-1] += "\n"

    with open(g_disasm_file, "w") as disasm_file:
        disasm_file.write("\n".join(file_contents))


def build_cfg_and_analyze():
    """Build cfg and perform symbolic execution"""
    change_format()
    log.info("Building CFG...")
    with open(g_disasm_file, "r") as disasm_file:
        disasm_file.readline()  # Remove first line
        tokens = tokenize.generate_tokens(disasm_file.readline)  # tokenization
        collect_vertices(tokens)  # find vertices
        construct_bb()
        construct_static_edges()  # find static edges from stack top
        full_sym_exec()  # jump targets are constructed on the fly


def print_cfg():
    for block in vertices.values():
        block.display()
    log.debug(str(edges))


def mapping_push_instruction(
    current_line_content, current_ins_address, idx, positions, length
):
    global g_src_map
    while idx < length:
        if not positions[idx]:
            return idx + 1
        name = positions[idx]["name"]
        if name.startswith("tag"):
            idx += 1
        else:
            if name.startswith("PUSH"):
                if name == "PUSH":
                    value = positions[idx]["value"]
                    instr_value = current_line_content.split(" ")[1]
                    if int(value, 16) == int(instr_value, 16):
                        g_src_map.instr_positions[current_ins_address] = (
                            g_src_map.positions[idx]
                        )
                        idx += 1
                        break
                    else:
                        # print(idx, positions[idx])
                        # print(value, instr_value, current_line_content)
                        raise Exception("Source map error")
                else:
                    g_src_map.instr_positions[current_ins_address] = (
                        g_src_map.positions[idx]
                    )
                    idx += 1
                    break
            else:
                raise Exception("Source map error")
    return idx


def mapping_non_push_instruction(
    current_line_content, current_ins_address, idx, positions, length
):
    global g_src_map
    while idx < length:
        if not positions[idx]:
            return idx + 1
        name = positions[idx]["name"]
        if name.startswith("tag"):
            idx += 1
        else:
            instr_name = current_line_content.split(" ")[0]
            if (
                name == instr_name
                or name == "INVALID"
                and instr_name == "ASSERTFAIL"
                or name == "KECCAK256"
                and instr_name == "SHA3"
                or name == "SELFDESTRUCT"
                and instr_name == "SUICIDE"
            ):
                g_src_map.instr_positions[current_ins_address] = g_src_map.positions[
                    idx
                ]
                idx += 1
                break
            else:
                raise RuntimeError(
                    f"Source map error, unknown name({name}) or instr_name({instr_name})"
                )
    return idx


# 1. Parse the disassembled file
# 2. Then identify each basic block (i.e. one-in, one-out)
# 3. Store them in vertices


def collect_vertices(tokens):
    global g_src_map
    if g_src_map:
        idx = 0
        positions = g_src_map.positions
        length = len(positions)
    global end_ins_dict
    global instructions
    global jump_type

    current_ins_address = 0
    last_ins_address = 0
    is_new_line = True
    current_block = 0
    current_line_content = ""
    wait_for_push = False
    is_new_block = False

    for tok_type, tok_string, (srow, scol), _, line_number in tokens:
        if wait_for_push is True:
            push_val = ""
            if current_line_content == "PUSH0 " and tok_type == NEWLINE:
                is_new_line = True
                current_line_content += "0 "
                instructions[current_ins_address] = current_line_content
                idx = (
                        mapping_push_instruction(
                        current_line_content,
                        current_ins_address,
                        idx,
                        positions,
                        length,
                    )
                    if g_src_map
                    else None
                )
                current_line_content = ""
                wait_for_push = False
                continue

            for ptok_type, ptok_string, _, _, _ in tokens:
                if ptok_type == NEWLINE:
                    is_new_line = True
                    current_line_content += push_val + " "
                    instructions[current_ins_address] = current_line_content
                    idx = (
                        mapping_push_instruction(
                            current_line_content,
                            current_ins_address,
                            idx,
                            positions,
                            length,
                        )
                        if g_src_map
                        else None
                    )
                    current_line_content = ""
                    wait_for_push = False
                    break
                try:
                    int(ptok_string, 16)
                    push_val += ptok_string
                except ValueError:
                    pass

            continue
        elif is_new_line is True and tok_type == NUMBER:  # looking for a line number
            last_ins_address = current_ins_address
            try:
                current_ins_address = int(tok_string)
            except ValueError:
                log.critical("ERROR when parsing row %d col %d", srow, scol)
                quit()
            is_new_line = False
            if is_new_block:
                current_block = current_ins_address
                is_new_block = False
            continue
        elif tok_type == NEWLINE:
            is_new_line = True
            log.debug(current_line_content)
            instructions[current_ins_address] = current_line_content
            idx = (
                mapping_non_push_instruction(
                    current_line_content, current_ins_address, idx, positions, length
                )
                if g_src_map
                else None
            )
            current_line_content = ""
            continue
        elif tok_type == NAME:
            if tok_string == "JUMPDEST":
                if last_ins_address not in end_ins_dict:
                    end_ins_dict[current_block] = last_ins_address
                current_block = current_ins_address
                is_new_block = False
            elif (
                tok_string == "STOP"
                or tok_string == "RETURN"
                or tok_string == "SUICIDE"
                or tok_string == "REVERT"
                or tok_string == "ASSERTFAIL"
            ):
                jump_type[current_block] = "terminal"
                end_ins_dict[current_block] = current_ins_address
            elif tok_string == "JUMP":
                jump_type[current_block] = "unconditional"
                end_ins_dict[current_block] = current_ins_address
                is_new_block = True
            elif tok_string == "JUMPI":
                jump_type[current_block] = "conditional"
                end_ins_dict[current_block] = current_ins_address
                is_new_block = True
            elif tok_string.startswith("PUSH", 0):
                wait_for_push = True
            is_new_line = False
        if tok_string != "=" and tok_string != ">":
            current_line_content += tok_string + " "

    if current_block not in end_ins_dict:
        log.debug("current block: %d", current_block)
        log.debug("last line: %d", current_ins_address)
        end_ins_dict[current_block] = current_ins_address

    if current_block not in jump_type:
        jump_type[current_block] = "terminal"

    for key in end_ins_dict:
        if key not in jump_type:
            jump_type[key] = "falls_to"


def construct_bb():
    global vertices
    global edges
    global blocks
    sorted_addresses = sorted(instructions.keys())
    size = len(sorted_addresses)
    # logging.info("instruction size: %d" % size)
    for key in end_ins_dict:
        end_address = end_ins_dict[key]
        block = BasicBlock(key, end_address)
        if key not in instructions:
            continue
        block.add_instruction(instructions[key])
        i = sorted_addresses.index(key) + 1
        while i < size and sorted_addresses[i] <= end_address:
            block.add_instruction(instructions[sorted_addresses[i]])
            i += 1
        block.set_block_type(jump_type[key])
        vertices[key] = block
        blocks[key] = end_address
        edges[key] = []


def construct_static_edges():
    add_falls_to()  # these edges are static


def add_falls_to():
    global vertices
    global edges
    key_list = sorted(jump_type.keys())
    length = len(key_list)
    for i, key in enumerate(key_list):
        if (
            jump_type[key] != "terminal"
            and jump_type[key] != "unconditional"
            and i + 1 < length
        ):
            target = key_list[i + 1]
            edges[key].append(target)
            vertices[key].set_falls_to(target)


def get_init_global_state(path_conditions_and_vars):
    global_state = {"balance": {}, "pc": 0}
    init_is = init_ia = deposited_value = sender_address = receiver_address = (
        gas_price
    ) = origin = currentCoinbase = currentNumber = currentDifficulty = (
        currentGasLimit
    ) = currentChainId = currentSelfBalance = currentBaseFee = callData = None

    sender_address = BitVec("Is", 256)
    receiver_address = BitVec("Ia", 256)
    deposited_value = BitVec("Iv", 256)
    init_is = BitVec("init_Is", 256)
    init_ia = BitVec("init_Ia", 256)

    path_conditions_and_vars["Is"] = sender_address
    path_conditions_and_vars["Ia"] = receiver_address
    path_conditions_and_vars["Iv"] = deposited_value

    # from s to a, s is sender, a is receiver
    # v is the amount of ether deposited and transferred
    constraint = deposited_value >= BitVecVal(0, 256)
    path_conditions_and_vars["path_condition"].append(constraint)
    constraint = init_is >= deposited_value
    path_conditions_and_vars["path_condition"].append(constraint)
    constraint = init_ia >= BitVecVal(0, 256)
    path_conditions_and_vars["path_condition"].append(constraint)

    # update the balances of the "caller" and "callee"
    global_state["balance"]["Is"] = init_is - deposited_value
    global_state["balance"]["Ia"] = init_ia + deposited_value

    if not gas_price:
        new_var_name = gen.gen_gas_price_var()
        gas_price = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = gas_price

    if not origin:
        new_var_name = gen.gen_origin_var()
        origin = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = origin

    if not currentCoinbase:
        new_var_name = "IH_c"
        currentCoinbase = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = currentCoinbase

    if not currentNumber:
        new_var_name = "IH_i"
        currentNumber = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = currentNumber

    if not currentDifficulty:
        new_var_name = "IH_d"
        currentDifficulty = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = currentDifficulty

    if not currentGasLimit:
        new_var_name = "IH_l"
        currentGasLimit = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = currentGasLimit

    if not currentChainId:
        new_var_name = "IH_cid"
        currentChainId = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = currentChainId

    if not currentSelfBalance:
        new_var_name = "IH_b"
        currentSelfBalance = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = currentSelfBalance

    if not currentBaseFee:
        new_var_name = "IH_f"
        currentBaseFee = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = currentBaseFee

    new_var_name = "IH_s"
    currentTimestamp = BitVec(new_var_name, 256)
    path_conditions_and_vars[new_var_name] = currentTimestamp

    # the state of the current contract
    if "Ia" not in global_state:
        global_state["Ia"] = {}
    global_state["miu_i"] = 0
    global_state["value"] = deposited_value
    global_state["sender_address"] = sender_address
    global_state["receiver_address"] = receiver_address
    global_state["gas_price"] = gas_price
    global_state["origin"] = origin
    global_state["currentCoinbase"] = currentCoinbase
    global_state["currentTimestamp"] = currentTimestamp
    global_state["currentNumber"] = currentNumber
    global_state["currentDifficulty"] = currentDifficulty
    global_state["currentGasLimit"] = currentGasLimit

    global_state["currentChainId"] = currentChainId
    global_state["currentSelfBalance"] = currentSelfBalance
    global_state["currentBaseFee"] = currentBaseFee

    # the state of gates to detect each defect
    global_state["ERC721_reentrancy"] = {
        "pc": [],
        "key": None,
        "check": False,
        "var": [],
    }

    global_state["standard_violation"] = {
        "mint_pc": [],
        "approve_pc": [],
        "setApprovalForAll_pc": [],
    }

    global_state["unlimited_minting"] = {
        "pc": [],
        "check": False,
    }

    global_state["mint"] = {
        "trigger": False,
        "to": None,
        "token_id": None,
        "quantity": None,
        "hash": None,
        "MSTORE_1": False,
        "MSTORE_2": False,
        "valid": False,
    }

    global_state["approve"] = {
        "trigger": False,
        "to": None,
        "token_id": None,
        # *Load owner before approval
        "owner_hash": None,
        "hash": None,
        "MSTORE_1": False,
        "MSTORE_2": False,
        # *Note the hash of owner(_owners[tokenId])
        "MSTORE_owner": False,
        "valid": False,
    }

    global_state["transfer"] = {
        "trigger": False,
        "to": None,
        "token_id": None,
        "from": None,
        "MSTORE_owner": False,
        "owner_hash": None,
        "MSTORE_2": False,
    }

    global_state["setApprovalForAll"] = {
        "trigger": False,
        "operator": None,
        "approved": None,
        "MSTORE_1": False,
        "MSTORE_2": False,
        "MSTORE_3": False,
        "hash": None,
        "valid": False,
    }

    global_state["burn"] = {
        "trigger": False,
        "token_id": None,
        "hash": None,
        "MSTORE_1": False,
        "MSTORE_2": False,
        "sload": None,
        "valid": False,
        "pc": None,
    }

    return global_state


def get_start_block_to_func_sig():
    """Map block to function signature

    Returns:
        dict: pc tp function signature
    """
    state = 0
    func_sig = None
    for pc, instr in six.iteritems(instructions):
        if state == 0 and instr.startswith("PUSH4"):
            state += 1
            func_sig = instr.split(" ")[1][2:]
        elif state == 1 and instr.startswith("EQ"):
            state += 1
        elif state == 2 and instr.startswith("PUSH"):
            state = 0
            pc = instr.split(" ")[1]
            pc = int(pc, 16)
            start_block_to_func_sig[pc] = func_sig
        else:
            state = 0
    return start_block_to_func_sig


def full_sym_exec():
    global results
    global _from
    global _to
    global _tokenId
    global count
    global owner
    global return_owner
    global test_results
    global pre_func_name
    global sstore_mark
    global ERC721A_load_type
    global ERC721Pausable_trait
    ERC721Pausable_trait = False
    ERC721A_load_type = False
    sstore_mark = False
    test_results = [[0], [0], [0]]
    pre_func_name = ""
    _from = _to = _tokenId = owner = None
    count = 0

    # find expression of return_owner in AST
    try:
        if global_params.IS_LOW_VERSION:
            return_owner = find_return_owner_LV()
        else:
            return_owner = find_return_owner()
    except:
        return_owner = "return owner"
    if return_owner == None:
        return_owner = "return owner"

    # executing, starting from beginning
    path_conditions_and_vars = {"path_condition": []}
    global_state = get_init_global_state(path_conditions_and_vars)
    analysis = init_analysis()
    params = Parameter(
        path_conditions_and_vars=path_conditions_and_vars,
        global_state=global_state,
        analysis=analysis,
    )
    # start_block = 0
    # if g_src_map:
    #     start_block_to_func_sig = get_start_block_to_func_sig()
    #     logging.info(start_block_to_func_sig)
    #     if global_params.TARGET_FUNCTION:
    #         start_block = list(start_block_to_func_sig.keys())[
    #             list(start_block_to_func_sig.values()).index(
    #                 global_params.TARGET_FUNCTION
    #             )
    #         ]
    # with live:
    #     sym_exec_block(params, start_block, 0, 0, -1, "fallback")
    
    start_blocks = []
    if g_src_map:
        start_block_to_func_sig = get_start_block_to_func_sig()
        logging.info(start_block_to_func_sig)
        if global_params.TARGET_FUNCTION:
            start_blocks.append(list(start_block_to_func_sig.keys())[
                list(start_block_to_func_sig.values()).index(
                    global_params.TARGET_FUNCTION
                )
            ])
        # To reduce the running time 
        # select those functions which contain "emit Trnasfer" instead of checking all the functions in contract
        else:
            try:
                if global_params.IS_LOW_VERSION:
                    target_functions = get_target_functions_LV(g_src_map.cname)
                else:
                    target_functions = get_target_functions(g_src_map.cname)
                for function in target_functions:
                    for func_sig in g_src_map.sig_to_func:
                        if function in g_src_map.sig_to_func[func_sig]:
                            try:
                                start_blocks.append(list(start_block_to_func_sig.keys())[
                                    list(start_block_to_func_sig.values()).index(
                                        func_sig
                                    )
                                ])
                            except Exception as e:
                                print(e)
            except Exception as e:
                print(e)
            try:
                defualt_block = list(start_block_to_func_sig.keys())[
                    list(start_block_to_func_sig.values()).index("23b872dd")]
                if defualt_block not in start_blocks:
                    start_blocks.insert(0, defualt_block)
            except:
                pass

    with live:
        for start_block in start_blocks:
            pre_length3 = len(test_results[2])
            sym_exec_block(params, start_block, 0, 0, -1, "fallback")
            if len(test_results[2]) > pre_length3 and sstore_mark:
                for i in range(pre_length3, len(test_results[2])):
                    if test_results[2][i].split(":")[1] == "standard1":
                        test_results[2].pop(i)
                        break
                if len(test_results[2]) == 1:
                    test_results[2][0] = 0
            # print("return_owner: ", return_owner)
            # print("_from: ", _from)
            # print("_to: ", _to)
            # print("_tokenId: ", _tokenId)
            # print("owner: ", owner)

        if not start_blocks:
            test_results = [[-1], [-1], [-1]]
        elif owner == None:
            test_results[0] = [-2]
            test_results[1] = [-2]
        elif ERC721A_load_type:
            test_results[1] = [0]
        if "ERC721Pausable" in g_src_map.source.content and len(test_results[1]) > 1:
            for i in range(1, len(test_results[1])):
                var_name = test_results[1][i].split(":")[1].split("-")[-1]
                if var_name == "_owner" and ERC721Pausable_trait:
                    test_results[1].remove(test_results[1][i])
            if len(test_results[1]) == 1:
                test_results[1][0] = 0
        # with open("test_record.txt", 'a+', encoding="utf-8") as f:
        #     content = str(test_results) + ", "
        #     f.write(content)
        for i in range(3):
            if test_results[i][0] == 1:
                if i == 0:
                    results["bool_defect"]["unrestricted_from_and_owner_inconsistency"] = True
                    for j in range(1, len(test_results[i])):
                        results["analysis"]["unrestricted_from_and_owner_inconsistency"].append(test_results[i][j])
                elif i == 1:
                    results["bool_defect"]["privileged_address"] = True
                    for j in range(1, len(test_results[i])):
                        results["analysis"]["privileged_address"].append(test_results[i][j])
                elif i == 2:
                    results["bool_defect"]["empty_transfer_event"] = True
                    for j in range(1, len(test_results[i])):
                        results["analysis"]["empty_transfer_event"].append(test_results[i][j])


# Symbolically executing a block from the start address
def sym_exec_block(params, block, pre_block, depth, func_call, current_func_name):
    global solver
    global visited_edges
    global money_flow_all_paths
    global path_conditions
    global global_problematic_pcs
    global all_gs
    global results
    global g_src_map
    global _from
    global _to
    global _tokenId
    global count
    global owner
    global return_owner
    global pre_func_name
    global sstore_mark
    global current_func
    global ERC721A_load_type
    global ERC721Pausable_trait

    visited = params.visited
    stack = params.stack
    mem = params.mem
    memory = params.memory
    global_state = params.global_state
    sha3_list = params.sha3_list
    path_conditions_and_vars = params.path_conditions_and_vars
    analysis = params.analysis
    calls = params.calls

    if current_func_name != pre_func_name:
        # print(pre_func_name, current_func_name, block)
        count = 0
        pre_func_name = current_func_name
        sstore_mark = False
    # if current_func_name == "assertOwnership":
    #     print("pause")
    # Factory Function for tuples is used as dictionary key
    Edge = namedtuple("Edge", ["v1", "v2"])
    if block < 0:
        log.debug("UNKNOWN JUMP ADDRESS. TERMINATING THIS PATH")
        return ["ERROR"]

    log.debug("Reach block address %d \n", block)

    if g_src_map:
        if block in start_block_to_func_sig:
            func_sig = start_block_to_func_sig[block]
            current_func_name = g_src_map.sig_to_func[func_sig]
            # print(current_func_name)
            current_func = current_func_name
            pattern = r"(\w[\w\d_]*)\((.*)\)$"
            match = re.match(pattern, current_func_name)
            if match:
                current_func_name = list(match.groups())[0]

    current_edge = Edge(pre_block, block)
    if current_edge in visited_edges:
        updated_count_number = visited_edges[current_edge] + 1
        visited_edges.update({current_edge: updated_count_number})
    else:
        visited_edges.update({current_edge: 1})
    log.debug(current_edge)
    log.debug(visited_edges[current_edge])
    if visited_edges[current_edge] > global_params.LOOP_LIMIT:
        log.debug("Overcome a number of loop limit. Terminating this path ...")
        return stack

    current_gas_used = analysis["gas"]
    if current_gas_used > global_params.GAS_LIMIT:
        log.debug("Run out of gas. Terminating this path ... ")
        return stack

    # Execute every instruction, one at a time
    try:
        block_ins = vertices[block].get_instructions()
    except KeyError:
        log.debug("This path results in an exception, possibly an invalid jump address")
        return ["ERROR"]
    for instr in block_ins:
        source_code = g_src_map.get_source_code(global_state["pc"])
        instr = instr.strip()
        sym_exec_ins(params, block, instr, func_call, current_func_name)
        # print(instr, source_code)
        if source_code == 'require(!paused(), "ERC721Pausable: token transfer while paused")':
            ERC721Pausable_trait = True
        # if source_code == "_tokenOwner[tokenId] = to":
        #     print("-------------------------------------------------------")
        #     print(block, block_ins, len(block_ins))
        #     if "LOG4 " in block_ins:
        #         print("LOG4 exists.")
        #     print("-------------------------------------------------------")
        # if "_owner" in source_code:
        #     print(instr, source_code)
        # ERC721A
        if source_code == return_owner or  source_code == "prevOwnership.addr" or source_code == "return packed":
            owner = stack[0]
            # print("hello", source_code, owner)
        elif (source_code == "result := or(eq(msgSender, owner), eq(msgSender, approvedAddress))" or
              source_code == "result := or(eq(msgSender, from), eq(msgSender, approvedAddress))"):
            ERC721A_load_type = True
            # print(owner)
            # print("owner: ", owner)
        # if "require(_ownerOf(tokenId) == from" in source_code:
        #     print("----------------------------------------------------")
        #     print(solver)
        #     print("----------------------------------------------------")
        # elif source_code == "msg.sender == c_owner":
        #     print(stack)

    # Mark that this basic block in the visited blocks
    visited.append(block)
    depth += 1

    # Go to next Basic Block(s)
    if jump_type[block] == "terminal" or depth > global_params.DEPTH_LIMIT:
        global total_no_of_paths
        global no_of_test_cases

        total_no_of_paths += 1

        if global_params.GENERATE_TEST_CASES:
            try:
                model = solver.model()
                no_of_test_cases += 1
                filename = "test%s.otest" % no_of_test_cases
                with open(filename, "w") as f:
                    for variable in model.decls():
                        f.write(str(variable) + " = " + str(model[variable]) + "\n")
                if os.stat(filename).st_size == 0:
                    os.remove(filename)
                    no_of_test_cases -= 1
            except Exception:
                pass

        log.debug("TERMINATING A PATH ...")
        # display_analysis(analysis)
        if is_testing_evm():
            compare_storage_and_gas_unit_test(global_state, analysis)

    elif jump_type[block] == "unconditional":  # executing "JUMP"
        successor = vertices[block].get_jump_target()
        new_params = params.copy()
        new_params.global_state["pc"] = successor
        if g_src_map:
            source_code = g_src_map.get_source_code(global_state["pc"])
            if source_code in g_src_map.func_call_names:
                func_call = global_state["pc"]
        sym_exec_block(
            new_params, successor, block, depth, func_call, current_func_name
        )
    elif jump_type[block] == "falls_to":  # just follow to the next basic block
        successor = vertices[block].get_falls_to()
        new_params = params.copy()
        new_params.global_state["pc"] = successor
        sym_exec_block(
            new_params, successor, block, depth, func_call, current_func_name
        )
    elif jump_type[block] == "conditional":  # executing "JUMPI"
        # A choice point, we proceed with depth first search

        branch_expression = vertices[block].get_branch_expression()
        
        log.debug("Branch expression: " + str(branch_expression))
        # log.info("Branch expression: " + str(branch_expression))

        solver.push()  # SET A BOUNDARY FOR SOLVER
        solver.add(branch_expression)
        # if current_func_name == "transferFrom":
        #     print("-------------------------2-----------------------------")
        #     print(solver)
        try:
            if solver.check() == unsat:
                log.debug("INFEASIBLE PATH DETECTED")
            else:
                left_branch = vertices[block].get_jump_target()
                
                new_params = params.copy()
                new_params.global_state["pc"] = left_branch
                new_params.path_conditions_and_vars["path_condition"].append(
                    branch_expression
                )
                sym_exec_block(
                    new_params, left_branch, block, depth, func_call, current_func_name
                )
        except TimeoutError:
            raise
        except Exception:
            if global_params.DEBUG_MODE:
                traceback.print_exc()

        solver.pop()  # POP SOLVER CONTEXT

        solver.push()  # SET A BOUNDARY FOR SOLVER
        negated_branch_expression = Not(branch_expression)
        solver.add(negated_branch_expression)

        log.debug("Negated branch expression: " + str(negated_branch_expression))

        try:
            if solver.check() == unsat:
                # Note that this check can be optimized. I.e. if the previous check succeeds,
                # no need to check for the negated condition, but we can immediately go into
                # the else branch
                log.debug("INFEASIBLE PATH DETECTED")
            else:
                right_branch = vertices[block].get_falls_to()
                new_params = params.copy()
                new_params.global_state["pc"] = right_branch
                new_params.path_conditions_and_vars["path_condition"].append(
                    negated_branch_expression
                )
                sym_exec_block(
                    new_params, right_branch, block, depth, func_call, current_func_name
                )
        except TimeoutError:
            raise
        except Exception:
            if global_params.DEBUG_MODE:
                traceback.print_exc()
        solver.pop()  # POP SOLVER CONTEXT
        updated_count_number = visited_edges[current_edge] - 1
        visited_edges.update({current_edge: updated_count_number})
    else:
        updated_count_number = visited_edges[current_edge] - 1
        visited_edges.update({current_edge: updated_count_number})
        raise Exception("Unknown Jump-Type")


# Symbolically executing an instruction
def sym_exec_ins(params, block, instr, func_call, current_func_name):
    global MSIZE
    global visited_pcs
    global solver
    global vertices
    global edges
    global blocks
    global g_src_map
    global g_slot_map
    global calls_affect_state
    global instructions
    global _from
    global _to
    global _tokenId
    global count
    global owner
    global return_owner
    global test_results
    global sstore_mark
    global current_func

    stack = params.stack
    mem = params.mem
    memory = params.memory
    global_state = params.global_state
    sha3_list = params.sha3_list
    path_conditions_and_vars = params.path_conditions_and_vars
    analysis = params.analysis
    calls = params.calls
    overflow_pcs = params.overflow_pcs

    visited_pcs.add(global_state["pc"])

    instr_parts = str.split(instr, " ")
    
    opcode = instr_parts[0]

    if opcode == "INVALID":
        return
    elif opcode == "ASSERTFAIL":
        return
    # collecting the analysis result by calling this skeletal function
    # this should be done before symbolically executing the instruction,
    # since SE will modify the stack and mem
    # semantic_analysis(
    #     analysis,
    #     opcode,
    #     stack,
    #     mem,
    #     global_state,
    #     global_problematic_pcs,
    #     current_func_name,
    #     g_src_map,
    #     path_conditions_and_vars,
    #     solver,
    #     instructions,
    #     g_slot_map,
    # )
    sleepmint_analysis(opcode, stack, solver, _from, owner, test_results, sstore_mark, current_func)
    
    # block coverage
    total_blocks = len(vertices)
    visited_blocks.add(block)
    block_coverage = len(visited_blocks) / total_blocks * 100

    # instruction coverage
    perc = float(len(visited_pcs)) / len(instructions.keys()) * 100
    # update per 5% change in code coverage
    if int(perc) % 5 == 0:
        live.update(
            generate_table(
                opcode,
                block_coverage,
                global_state["pc"],
                perc,
                g_src_map,
                global_problematic_pcs,
                current_func_name,
            ),
            refresh=True,
        )

    log.debug("===============" + current_func_name + "===============")
    log.debug("EXECUTING: " + instr)

    #
    #  0s: Stop and Arithmetic Operations
    #
    
    if opcode == "STOP":
        global_state["pc"] = global_state["pc"] + 1
        return
    elif opcode == "ADD":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            # Type conversion is needed when they are mismatched
            if isReal(first) and isSymbolic(second):
                first = BitVecVal(first, 256)
                computed = first + second
            elif isSymbolic(first) and isReal(second):
                second = BitVecVal(second, 256)
                computed = first + second
            else:
                # both are real and we need to manually modulus with 2 ** 256
                # if both are symbolic z3 takes care of modulus automatically
                computed = (first + second) % (2**256)
            computed = simplify(computed) if is_expr(computed) else computed

            check_revert = False
            if jump_type[block] == "conditional":
                jump_target = vertices[block].get_jump_target()
                falls_to = vertices[block].get_falls_to()
                check_revert = any(
                    [
                        True
                        for instruction in vertices[jump_target].get_instructions()
                        if instruction.startswith("REVERT")
                    ]
                )
                if not check_revert:
                    check_revert = any(
                        [
                            True
                            for instruction in vertices[falls_to].get_instructions()
                            if instruction.startswith("REVERT")
                        ]
                    )

            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "MUL":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isReal(first) and isSymbolic(second):
                first = BitVecVal(first, 256)
            elif isSymbolic(first) and isReal(second):
                second = BitVecVal(second, 256)
            computed = first * second & UNSIGNED_BOUND_NUMBER
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "SUB":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isReal(first) and isSymbolic(second):
                first = BitVecVal(first, 256)
                computed = first - second
            elif isSymbolic(first) and isReal(second):
                second = BitVecVal(second, 256)
                computed = first - second
            else:
                computed = (first - second) % (2**256)
            computed = simplify(computed) if is_expr(computed) else computed

            check_revert = False
            if jump_type[block] == "conditional":
                jump_target = vertices[block].get_jump_target()
                falls_to = vertices[block].get_falls_to()
                check_revert = any(
                    [
                        True
                        for instruction in vertices[jump_target].get_instructions()
                        if instruction.startswith("REVERT")
                    ]
                )
                if not check_revert:
                    check_revert = any(
                        [
                            True
                            for instruction in vertices[falls_to].get_instructions()
                            if instruction.startswith("REVERT")
                        ]
                    )

            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "DIV":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isAllReal(first, second):
                if second == 0:
                    computed = 0
                else:
                    first = to_unsigned(first)
                    second = to_unsigned(second)
                    computed = first / second
            else:
                first = to_symbolic(first)
                second = to_symbolic(second)
                solver.push()
                solver.add(Not(second == 0))
                if check_sat(solver) == unsat:
                    computed = 0
                else:
                    computed = UDiv(first, second)
                solver.pop()
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "SDIV":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isAllReal(first, second):
                first = to_signed(first)
                second = to_signed(second)
                if second == 0:
                    computed = 0
                elif first == -(2**255) and second == -1:
                    computed = -(2**255)
                else:
                    sign = -1 if (first / second) < 0 else 1
                    computed = sign * (abs(first) / abs(second))
            else:
                first = to_symbolic(first)
                second = to_symbolic(second)
                solver.push()
                solver.add(Not(second == 0))
                if check_sat(solver) == unsat:
                    computed = 0
                else:
                    solver.push()
                    solver.add(Not(And(first == -(2**255), second == -1)))
                    if check_sat(solver) == unsat:
                        computed = -(2**255)
                    else:
                        solver.push()
                        solver.add(first / second < 0)
                        sign = -1 if check_sat(solver) == sat else 1

                        def z3_abs(x):
                            return If(x >= 0, x, -x)

                        first = z3_abs(first)
                        second = z3_abs(second)
                        computed = sign * (first / second)
                        solver.pop()
                    solver.pop()
                solver.pop()
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "MOD":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isAllReal(first, second):
                if second == 0:
                    computed = 0
                else:
                    first = to_unsigned(first)
                    second = to_unsigned(second)
                    computed = first % second & UNSIGNED_BOUND_NUMBER

            else:
                first = to_symbolic(first)
                second = to_symbolic(second)

                solver.push()
                solver.add(Not(second == 0))
                if check_sat(solver) == unsat:
                    # it is provable that second is indeed equal to zero
                    computed = 0
                else:
                    computed = URem(first, second)
                solver.pop()

            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "SMOD":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isAllReal(first, second):
                if second == 0:
                    computed = 0
                else:
                    first = to_signed(first)
                    second = to_signed(second)
                    sign = -1 if first < 0 else 1
                    computed = sign * (abs(first) % abs(second))
            else:
                first = to_symbolic(first)
                second = to_symbolic(second)

                solver.push()
                solver.add(Not(second == 0))
                if check_sat(solver) == unsat:
                    # it is provable that second is indeed equal to zero
                    computed = 0
                else:
                    solver.push()
                    solver.add(first < 0)  # check sign of first element
                    sign = (
                        BitVecVal(-1, 256)
                        if check_sat(solver) == sat
                        else BitVecVal(1, 256)
                    )
                    solver.pop()

                    def z3_abs(x):
                        return If(x >= 0, x, -x)

                    first = z3_abs(first)
                    second = z3_abs(second)

                    computed = sign * (first % second)
                solver.pop()

            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "ADDMOD":
        if len(stack) > 2:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            third = stack.pop(0)

            if isAllReal(first, second, third):
                if third == 0:
                    computed = 0
                else:
                    computed = (first + second) % third
            else:
                first = to_symbolic(first)
                second = to_symbolic(second)
                solver.push()
                solver.add(Not(third == 0))
                if check_sat(solver) == unsat:
                    computed = 0
                else:
                    first = ZeroExt(256, first)
                    second = ZeroExt(256, second)
                    third = ZeroExt(256, third)
                    computed = (first + second) % third
                    computed = Extract(255, 0, computed)
                solver.pop()
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "MULMOD":
        if len(stack) > 2:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            third = stack.pop(0)

            if isAllReal(first, second, third):
                if third == 0:
                    computed = 0
                else:
                    computed = (first * second) % third
            else:
                first = to_symbolic(first)
                second = to_symbolic(second)
                solver.push()
                solver.add(Not(third == 0))
                if check_sat(solver) == unsat:
                    computed = 0
                else:
                    first = ZeroExt(256, first)
                    second = ZeroExt(256, second)
                    third = ZeroExt(256, third)
                    computed = URem(first * second, third)
                    computed = Extract(255, 0, computed)
                solver.pop()
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "EXP":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            base = stack.pop(0)
            exponent = stack.pop(0)
            # Type conversion is needed when they are mismatched
            if isAllReal(base, exponent):
                computed = pow(base, exponent, 2**256)
            else:
                # The computed value is unknown, this is because power is
                # not supported in bit-vector theory
                new_var_name = gen.gen_arbitrary_var()
                computed = BitVec(new_var_name, 256)
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "SIGNEXTEND":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isAllReal(first, second):
                if first >= 32 or first < 0:
                    computed = second
                else:
                    signbit_index_from_right = 8 * first + 7
                    if second & (1 << signbit_index_from_right):
                        computed = second | (2**256 - (1 << signbit_index_from_right))
                    else:
                        computed = second & ((1 << signbit_index_from_right) - 1)
            else:
                first = to_symbolic(first)
                second = to_symbolic(second)
                solver.push()
                solver.add(Not(Or(first >= 32, first < 0)))
                if check_sat(solver) == unsat:
                    computed = second
                else:
                    signbit_index_from_right = 8 * first + 7
                    solver.push()
                    solver.add(second & (1 << signbit_index_from_right) == 0)
                    if check_sat(solver) == unsat:
                        computed = second | (2**256 - (1 << signbit_index_from_right))
                    else:
                        computed = second & ((1 << signbit_index_from_right) - 1)
                    solver.pop()
                solver.pop()
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    #
    #  10s: Comparison and Bitwise Logic Operations
    #
    elif opcode == "LT":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)

            if isAllReal(first, second):
                first = to_unsigned(first)
                second = to_unsigned(second)
                if first < second:
                    computed = 1
                else:
                    computed = 0
            else:
                computed = If(ULT(first, second), BitVecVal(1, 256), BitVecVal(0, 256))
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "GT":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)

            if isAllReal(first, second):
                first = to_unsigned(first)
                second = to_unsigned(second)
                if first > second:
                    computed = 1
                else:
                    computed = 0
            else:
                computed = If(UGT(first, second), BitVecVal(1, 256), BitVecVal(0, 256))
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "SLT":  # Not fully faithful to signed comparison
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isAllReal(first, second):
                first = to_signed(first)
                second = to_signed(second)
                if first < second:
                    computed = 1
                else:
                    computed = 0
            else:
                computed = If(first < second, BitVecVal(1, 256), BitVecVal(0, 256))
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "SGT":  # Not fully faithful to signed comparison
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isAllReal(first, second):
                first = to_signed(first)
                second = to_signed(second)
                if first > second:
                    computed = 1
                else:
                    computed = 0
            else:
                computed = If(first > second, BitVecVal(1, 256), BitVecVal(0, 256))
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "EQ":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            if isAllReal(first, second):
                if first == second:
                    computed = 1
                else:
                    computed = 0
            else:
                computed = If(first == second, BitVecVal(1, 256), BitVecVal(0, 256))
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "ISZERO":
        # Tricky: this instruction works on both boolean and integer,
        # when we have a symbolic expression, type error might occur
        # Currently handled by try and catch
        if len(stack) > 0:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            if isReal(first):
                if first == 0:
                    computed = 1
                else:
                    computed = 0
            else:
                computed = If(first == 0, BitVecVal(1, 256), BitVecVal(0, 256))
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "AND":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)
            computed = first & second
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "OR":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)

            computed = first | second
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)

        else:
            raise ValueError("STACK underflow")
    elif opcode == "XOR":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            second = stack.pop(0)

            computed = first ^ second
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)

        else:
            raise ValueError("STACK underflow")
    elif opcode == "NOT":
        if len(stack) > 0:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            computed = (~first) & UNSIGNED_BOUND_NUMBER
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "BYTE":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            first = stack.pop(0)
            byte_index = 32 - first - 1
            second = stack.pop(0)

            if isAllReal(first, second):
                if first >= 32 or first < 0:
                    computed = 0
                else:
                    computed = second & (255 << (8 * byte_index))
                    computed = computed >> (8 * byte_index)
            else:
                first = to_symbolic(first)
                second = to_symbolic(second)
                solver.push()
                solver.add(Not(Or(first >= 32, first < 0)))
                if check_sat(solver) == unsat:
                    computed = 0
                else:
                    computed = second & (255 << (8 * byte_index))
                    computed = computed >> (8 * byte_index)
                solver.pop()
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")
    #
    # 20s: SHA3/KECCAK256
    #
    elif opcode in ["KECCAK256", "SHA3"]:
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            s0 = stack.pop(0)  # 0
            s1 = stack.pop(0)  # 64
            slot = None
            if isAllReal(s0, s1):
                # simulate the hashing of sha3
                data = [str(x) for x in memory[s0 : s0 + s1]]

                # *Slot id in memory[63] <= MSTORE(64, slot)
                slot = memory[63]
                position = "".join(data)
                position = re.sub("[\s+]", "", position)
                position = zlib.compress(six.b(position), 9)
                position = base64.b64encode(position)
                position = position.decode("utf-8", "strict")
                if position in sha3_list:
                    stack.insert(0, sha3_list[position])
                else:
                    new_var_name = gen.gen_arbitrary_var()
                    new_var = BitVec(new_var_name, 256)
                    sha3_list[position] = new_var
                    stack.insert(0, new_var)
            else:
                # push into the execution a fresh symbolic variable
                new_var_name = gen.gen_arbitrary_var()
                new_var = BitVec(new_var_name, 256)
                path_conditions_and_vars[new_var_name] = new_var
                stack.insert(0, new_var)
            # find special stack&mem events during SE
            if global_state["mint"]["MSTORE_2"] == True:
                global_state["mint"]["hash"] = stack[0]
                global_state["mint"]["MSTORE_2"] = False
            elif global_state["approve"]["MSTORE_2"] == True:
                global_state["approve"]["hash"] = stack[0]
                global_state["approve"]["MSTORE_2"] = False
            elif global_state["approve"]["MSTORE_owner"] == True:
                global_state["approve"]["owner_hash"] = stack[0]
                global_state["approve"]["MSTORE_owner"] = False
            elif global_state["burn"]["MSTORE_2"] == True:
                global_state["burn"]["hash"] = stack[0]
                global_state["burn"]["MSTORE_2"] = False
            elif global_state["setApprovalForAll"]["MSTORE_3"] == True:
                global_state["setApprovalForAll"]["hash"] = stack[0]
                global_state["setApprovalForAll"]["MSTORE_3"] = False
            elif global_state["transfer"]["MSTORE_owner"] == True:
                global_state["transfer"]["owner_hash"] = stack[0]
                global_state["transfer"]["MSTORE_owner"] = False
            elif global_state["transfer"]["MSTORE_2"] == True:
                global_state["approve"]["hash"] = stack[0]
                global_state["transfer"]["MSTORE_2"] = False

        else:
            raise ValueError("STACK underflow")
    #
    # 30s: Environment Information
    #
    elif opcode == "ADDRESS":  # get address of currently executing account
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, path_conditions_and_vars["Ia"])
    elif opcode == "BALANCE":
        if len(stack) > 0:
            global_state["pc"] = global_state["pc"] + 1
            address = stack.pop(0)

            new_var_name = gen.gen_balance_var()
            if new_var_name in path_conditions_and_vars:
                new_var = path_conditions_and_vars[new_var_name]
            else:
                new_var = BitVec(new_var_name, 256)
                path_conditions_and_vars[new_var_name] = new_var
            if isReal(address):
                hashed_address = "concrete_address_" + str(address)
            else:
                hashed_address = str(address)
            global_state["balance"][hashed_address] = new_var
            stack.insert(0, new_var)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "CALLER":  # get caller address
        # that is directly responsible for this execution
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["sender_address"])
        # print("CALLER: ", stack)
    elif opcode == "ORIGIN":  # get execution origination address
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["origin"])
    elif opcode == "CALLVALUE":  # get value of this transaction
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["value"])
        # buy function feature: msg.value to transfer the token

    elif opcode == "CALLDATALOAD":  # from inputter data from environment
        if len(stack) > 0:
            global_state["pc"] = global_state["pc"] + 1
            position = stack.pop(0)
            if g_src_map:
                source_code = g_src_map.get_source_code(global_state["pc"] - 1)
                if (
                    source_code.startswith("function")
                    and isReal(position)
                    and current_func_name in g_src_map.func_name_to_params
                ):
                    params = g_src_map.func_name_to_params[current_func_name]
                    param_idx = (position - 4) // 32
                    for param in params:
                        if param_idx == param["position"]:
                            new_var_name = param["name"]
                            g_src_map.var_names.append(new_var_name)
                else:
                    new_var_name = gen.gen_data_var(position)
            else:
                new_var_name = gen.gen_data_var(position)
            if new_var_name in path_conditions_and_vars:
                new_var = path_conditions_and_vars[new_var_name]
            else:
                new_var = BitVec(new_var_name, 256)
                path_conditions_and_vars[new_var_name] = new_var
            stack.insert(0, new_var)
            count += 1
            if count == 1:
                _from = stack[0]
            elif count == 2:
                _to = stack[0]
            elif count == 3:
                _tokenId = stack[0]
        else:
            raise ValueError("STACK underflow")
    elif opcode == "CALLDATASIZE":
        global_state["pc"] = global_state["pc"] + 1
        new_var_name = gen.gen_data_size()
        if new_var_name in path_conditions_and_vars:
            new_var = path_conditions_and_vars[new_var_name]
        else:
            new_var = BitVec(new_var_name, 256)
            path_conditions_and_vars[new_var_name] = new_var
        stack.insert(0, new_var)
    elif opcode == "CALLDATACOPY":  # Copy inputter data to memory
        #  TODO: Don't know how to simulate this yet
        if len(stack) > 2:
            global_state["pc"] = global_state["pc"] + 1
            stack.pop(0)
            stack.pop(0)
            stack.pop(0)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "CODESIZE":
        global_state["pc"] = global_state["pc"] + 1
        if g_disasm_file.endswith(".disasm"):
            evm_file_name = g_disasm_file[:-7]
        else:
            evm_file_name = g_disasm_file
        with open(evm_file_name, "r") as evm_file:
            evm = evm_file.read()[:-1]
            code_size = len(evm) / 2
            stack.insert(0, code_size)
    elif opcode == "CODECOPY":
        if len(stack) > 2:
            global_state["pc"] = global_state["pc"] + 1
            mem_location = stack.pop(0)
            code_from = stack.pop(0)
            no_bytes = stack.pop(0)
            current_miu_i = global_state["miu_i"]

            if isAllReal(mem_location, current_miu_i, code_from, no_bytes):
                temp = int(math.ceil((mem_location + no_bytes) / float(32)))
                if temp > current_miu_i:
                    current_miu_i = temp

                if g_disasm_file.endswith(".disasm"):
                    evm_file_name = g_disasm_file[:-7]
                else:
                    evm_file_name = g_disasm_file
                with open(evm_file_name, "r") as evm_file:
                    evm = evm_file.read()[:-1]
                    start = code_from * 2
                    end = start + no_bytes * 2
                    code = evm[start:end]
                mem[mem_location] = int(code, 16)
            else:
                new_var_name = gen.gen_code_var("Ia", code_from, no_bytes)
                if new_var_name in path_conditions_and_vars:
                    new_var = path_conditions_and_vars[new_var_name]
                else:
                    new_var = BitVec(new_var_name, 256)
                    path_conditions_and_vars[new_var_name] = new_var

                temp = ((mem_location + no_bytes) / 32) + 1
                current_miu_i = to_symbolic(current_miu_i)
                expression = current_miu_i < temp
                solver.push()
                solver.add(expression)
                if MSIZE:
                    if check_sat(solver) != unsat:
                        current_miu_i = If(expression, temp, current_miu_i)
                solver.pop()
                mem.clear()  # very conservative
                mem[str(mem_location)] = new_var
            global_state["miu_i"] = current_miu_i
        else:
            raise ValueError("STACK underflow")
    elif opcode == "RETURNDATACOPY":
        if len(stack) > 2:
            global_state["pc"] += 1
            stack.pop(0)
            stack.pop(0)
            stack.pop(0)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "RETURNDATASIZE":
        global_state["pc"] += 1
        new_var_name = gen.gen_arbitrary_var()
        new_var = BitVec(new_var_name, 256)
        stack.insert(0, new_var)
    elif opcode == "GASPRICE":
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["gas_price"])
    elif opcode == "EXTCODESIZE":
        if len(stack) > 0:
            global_state["pc"] = global_state["pc"] + 1
            address = stack.pop(0)

            # not handled yet
            new_var_name = gen.gen_code_size_var(address)
            if new_var_name in path_conditions_and_vars:
                new_var = path_conditions_and_vars[new_var_name]
            else:
                new_var = BitVec(new_var_name, 256)
                path_conditions_and_vars[new_var_name] = new_var
            stack.insert(0, new_var)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "EXTCODECOPY":
        if len(stack) > 3:
            global_state["pc"] = global_state["pc"] + 1
            address = stack.pop(0)
            mem_location = stack.pop(0)
            code_from = stack.pop(0)
            no_bytes = stack.pop(0)
            current_miu_i = global_state["miu_i"]

            new_var_name = gen.gen_code_var(address, code_from, no_bytes)
            if new_var_name in path_conditions_and_vars:
                new_var = path_conditions_and_vars[new_var_name]
            else:
                new_var = BitVec(new_var_name, 256)
                path_conditions_and_vars[new_var_name] = new_var

            temp = ((mem_location + no_bytes) / 32) + 1
            current_miu_i = to_symbolic(current_miu_i)
            expression = current_miu_i < temp
            solver.push()
            solver.add(expression)
            if MSIZE:
                if check_sat(solver) != unsat:
                    current_miu_i = If(expression, temp, current_miu_i)
            solver.pop()
            mem.clear()  # very conservative
            mem[str(mem_location)] = new_var
            global_state["miu_i"] = current_miu_i
        else:
            raise ValueError("STACK underflow")
    #
    #  40s: Block Information
    #
    elif opcode == "BLOCKHASH":  # information from block header
        if len(stack) > 0:
            global_state["pc"] = global_state["pc"] + 1
            stack.pop(0)
            new_var_name = "IH_blockhash"
            if new_var_name in path_conditions_and_vars:
                new_var = path_conditions_and_vars[new_var_name]
            else:
                new_var = BitVec(new_var_name, 256)
                path_conditions_and_vars[new_var_name] = new_var
            stack.insert(0, new_var)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "COINBASE":  # information from block header
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["currentCoinbase"])
    elif opcode == "TIMESTAMP":  # information from block header
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["currentTimestamp"])
    elif opcode == "NUMBER":  # information from block header
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["currentNumber"])
    elif opcode == "DIFFICULTY":  # information from block header
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["currentDifficulty"])
    elif opcode == "GASLIMIT":  # information from block header
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["currentGasLimit"])
    #
    #  50s: Stack, Memory, Storage, and Flow Information
    #
    elif opcode == "POP":
        if len(stack) > 0:
            global_state["pc"] = global_state["pc"] + 1
            stack.pop(0)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "MLOAD":
        if len(stack) > 0:
            global_state["pc"] = global_state["pc"] + 1
            address = stack.pop(0)
            current_miu_i = global_state["miu_i"]
            if isAllReal(address, current_miu_i) and address in mem:
                temp = int(math.ceil((address + 32) / float(32)))
                if temp > current_miu_i:
                    current_miu_i = temp
                value = mem[address]
                stack.insert(0, value)
            else:
                temp = ((address + 31) / 32) + 1
                current_miu_i = to_symbolic(current_miu_i)
                expression = current_miu_i < temp
                solver.push()
                solver.add(expression)
                if MSIZE:
                    if check_sat(solver) != unsat:
                        # this means that it is possibly that current_miu_i < temp
                        current_miu_i = If(expression, temp, current_miu_i)
                solver.pop()
                new_var_name = gen.gen_mem_var(address)
                if new_var_name in path_conditions_and_vars:
                    new_var = path_conditions_and_vars[new_var_name]
                else:
                    new_var = BitVec(new_var_name, 256)
                    path_conditions_and_vars[new_var_name] = new_var
                stack.insert(0, new_var)
                if isReal(address):
                    mem[address] = new_var
                else:
                    mem[str(address)] = new_var
            global_state["miu_i"] = current_miu_i
        else:
            raise ValueError("STACK underflow")
    elif opcode == "MSTORE":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            stored_address = stack.pop(0)
            stored_value = stack.pop(0)
            # MSTORE slotid to MEM32

            current_miu_i = global_state["miu_i"]
            if isReal(stored_address):
                # preparing data for hashing later
                old_size = len(memory) // 32
                new_size = ceil32(stored_address + 32) // 32
                mem_extend = (new_size - old_size) * 32
                memory.extend([0] * mem_extend)
                value = stored_value

                for i in range(31, -1, -1):
                    memory[stored_address + i] = value % 256
                    value /= 256
            if isAllReal(stored_address, current_miu_i):
                temp = int(math.ceil((stored_address + 32) / float(32)))
                if temp > current_miu_i:
                    current_miu_i = temp
                # note that the stored_value could be symbolic
                mem[stored_address] = stored_value
            else:
                temp = ((stored_address + 31) / 32) + 1
                expression = current_miu_i < temp
                solver.push()
                solver.add(expression)
                if MSIZE:
                    if check_sat(solver) != unsat:
                        # this means that it is possibly that current_miu_i < temp
                        current_miu_i = If(expression, temp, current_miu_i)
                solver.pop()
                mem.clear()  # very conservative
                mem[str(stored_address)] = stored_value
            global_state["miu_i"] = current_miu_i
        else:
            raise ValueError("STACK underflow")
    elif opcode == "MSTORE8":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            stored_address = stack.pop(0)
            temp_value = stack.pop(0)
            stored_value = temp_value % 256  # get the least byte
            current_miu_i = global_state["miu_i"]
            if isAllReal(stored_address, current_miu_i):
                temp = int(math.ceil((stored_address + 1) / float(32)))
                if temp > current_miu_i:
                    current_miu_i = temp
                # note that the stored_value could be symbolic
                mem[stored_address] = stored_value
            else:
                temp = (stored_address / 32) + 1
                if isReal(current_miu_i):
                    current_miu_i = BitVecVal(current_miu_i, 256)
                expression = current_miu_i < temp
                solver.push()
                solver.add(expression)
                if MSIZE:
                    if check_sat(solver) != unsat:
                        # this means that it is possibly that current_miu_i < temp
                        current_miu_i = If(expression, temp, current_miu_i)
                solver.pop()
                mem.clear()  # very conservative
                mem[str(stored_address)] = stored_value
            global_state["miu_i"] = current_miu_i
        else:
            raise ValueError("STACK underflow")
    elif opcode == "SLOAD":
        if len(stack) > 0:
            global_state["pc"] = global_state["pc"] + 1
            position = stack.pop(0)

            if isReal(position) and position in global_state["Ia"]:
                value = global_state["Ia"][position]
                stack.insert(0, value)
            else:
                if str(position) in global_state["Ia"]:
                    value = global_state["Ia"][str(position)]
                    stack.insert(0, value)
                else:
                    if is_expr(position):
                        position = simplify(position)
                    if g_src_map:
                        # ?Prev Edition to get param name
                        new_var_name = g_src_map.get_source_code(global_state["pc"] - 1)
                        operators = "[-+*/%|&^!><=]"
                        new_var_name = (
                            re.compile(operators).split(new_var_name)[0].strip()
                        )
                        # judge the load operation of storage varible
                        new_var_name = g_src_map.get_parameter_or_state_var(
                            new_var_name
                        )
                        if new_var_name:
                            new_var_name = gen.gen_owner_store_var(
                                position, new_var_name
                            )
                        else:
                            new_var_name = gen.gen_owner_store_var(position)
                    else:
                        new_var_name = gen.gen_owner_store_var(position)

                    if new_var_name in path_conditions_and_vars:
                        new_var = path_conditions_and_vars[new_var_name]
                    else:
                        new_var = BitVec(new_var_name, 256)
                        path_conditions_and_vars[new_var_name] = new_var
                    stack.insert(0, new_var)
                    if isReal(position):
                        global_state["Ia"][position] = new_var
                    else:
                        global_state["Ia"][str(position)] = new_var
            if global_state["burn"]["hash"] != None:
                global_state["burn"]["sload"] = stack[0]
            # print("SLOAD: ", stack[0])
        else:
            raise ValueError("STACK underflow")

    elif opcode == "SSTORE":
        sstore_mark = True
        if len(stack) > 1:
            for call_pc in calls:
                calls_affect_state[call_pc] = True
            global_state["pc"] = global_state["pc"] + 1
            stored_address = stack.pop(0)
            stored_value = stack.pop(0)

            if isReal(stored_address):
                # note that the stored_value could be unknown
                global_state["Ia"][stored_address] = stored_value
            else:
                # note that the stored_value could be unknown
                global_state["Ia"][str(stored_address)] = stored_value
        else:
            raise ValueError("STACK underflow")
    elif opcode == "JUMP":
        if len(stack) > 0:
            target_address = stack.pop(0)
            if isSymbolic(target_address):
                try:
                    target_address = int(str(simplify(target_address)))
                except:
                    raise TypeError("Target address must be an integer")
            vertices[block].set_jump_target(target_address)
            if target_address not in edges[block]:
                edges[block].append(target_address)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "JUMPI":
        # We need to prepare two branches
        if len(stack) > 1:
            target_address = stack.pop(0)

            if isSymbolic(target_address):
                try:
                    target_address = int(str(simplify(target_address)))
                except:
                    raise TypeError("Target address must be an integer")
            vertices[block].set_jump_target(target_address)
            flag = stack.pop(0)
            branch_expression = BitVecVal(0, 1) == BitVecVal(1, 1)
            if isReal(flag):
                if flag != 0:
                    branch_expression = True
            else:
                branch_expression = flag != 0
            vertices[block].set_branch_expression(branch_expression)
            if target_address not in edges[block]:
                edges[block].append(target_address)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "PC":
        stack.insert(0, global_state["pc"])
        global_state["pc"] = global_state["pc"] + 1
    elif opcode == "MSIZE":
        global_state["pc"] = global_state["pc"] + 1
        msize = 32 * global_state["miu_i"]
        stack.insert(0, msize)
    elif opcode == "GAS":
        # In general, we do not have this precisely. It depends on both
        # the initial gas and the amount has been depleted
        # we need o think about this in the future, in case precise gas
        # can be tracked
        global_state["pc"] = global_state["pc"] + 1
        new_var_name = gen.gen_gas_var()
        new_var = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = new_var
        stack.insert(0, new_var)
    elif opcode == "JUMPDEST":
        # Literally do nothing
        global_state["pc"] = global_state["pc"] + 1
    #
    #  60s & 70s: Push Operations
    #
    elif opcode.startswith("PUSH", 0):  # this is a push instruction
        position = int(opcode[4:], 10)
        global_state["pc"] = global_state["pc"] + 1 + position
        pushed_value = int(instr_parts[1], 16)
        stack.insert(0, pushed_value)
        if global_params.UNIT_TEST == 3:  # test evm symbolic
            stack[0] = BitVecVal(stack[0], 256)
    #
    #  80s: Duplication Operations
    #
    elif opcode.startswith("DUP", 0):
        global_state["pc"] = global_state["pc"] + 1
        position = int(opcode[3:], 10) - 1
        if len(stack) > position:
            duplicate = stack[position]
            stack.insert(0, duplicate)
        else:
            raise ValueError("STACK underflow")

    #
    #  90s: Swap Operations
    #
    elif opcode.startswith("SWAP", 0):
        global_state["pc"] = global_state["pc"] + 1
        position = int(opcode[4:], 10)
        if len(stack) > position:
            temp = stack[position]
            stack[position] = stack[0]
            stack[0] = temp
            # *Delete => SWAP, others => DUP2
            if stack[1] == global_state["burn"]["sload"]:
                global_state["burn"]["valid"] = True
                global_state["burn"]["trigger"] = False
        else:
            raise ValueError("STACK underflow")

    #
    #  a0s: Logging Operations
    #
    elif opcode in ("LOG0", "LOG1", "LOG2", "LOG3", "LOG4"):
        global_state["pc"] = global_state["pc"] + 1
        # We do not simulate these log operations
        num_of_pops = 2 + int(opcode[3:])
        while num_of_pops > 0:
            stack.pop(0)
            num_of_pops -= 1

    #
    #  f0s: System Operations
    #
    elif opcode in ["CREATE", "CREATE2"]:
        if len(stack) > 2:
            global_state["pc"] += 1
            stack.pop(0)
            stack.pop(0)
            stack.pop(0)
            new_var_name = gen.gen_arbitrary_var()
            new_var = BitVec(new_var_name, 256)
            stack.insert(0, new_var)
        else:
            raise ValueError("STACK underflow")
    elif opcode == "CALL":
        # TODO: Need to handle miu_i
        if len(stack) > 6:
            calls.append(global_state["pc"])
            for call_pc in calls:
                if call_pc not in calls_affect_state:
                    calls_affect_state[call_pc] = False
            global_state["pc"] = global_state["pc"] + 1
            outgas = stack.pop(0)
            recipient = stack.pop(0)
            transfer_amount = stack.pop(0)
            start_data_input = stack.pop(0)
            size_data_input = stack.pop(0)
            start_data_output = stack.pop(0)
            size_data_ouput = stack.pop(0)

            # in the paper, it is shaky when the size of data output is
            # min of stack[6] and the | o |

            if isReal(transfer_amount):
                if transfer_amount == 0:
                    stack.insert(0, 1)  # x = 0
                    return

            # Let us ignore the call depth
            balance_ia = global_state["balance"]["Ia"]
            is_enough_fund = transfer_amount <= balance_ia
            solver.push()
            solver.add(is_enough_fund)

            if check_sat(solver) == unsat:
                # this means not enough fund, thus the execution will result in exception
                solver.pop()
                stack.insert(0, 0)  # x = 0
            else:
                # the execution is possibly okay
                stack.insert(0, 1)  # x = 1
                solver.pop()
                solver.add(is_enough_fund)
                path_conditions_and_vars["path_condition"].append(is_enough_fund)
                last_idx = len(path_conditions_and_vars["path_condition"]) - 1
                # analysis["time_dependency_bug"][last_idx] = global_state["pc"] - 1
                new_balance_ia = balance_ia - transfer_amount
                global_state["balance"]["Ia"] = new_balance_ia
                address_is = path_conditions_and_vars["Is"]
                address_is = address_is & CONSTANT_ONES_159
                boolean_expression = recipient != address_is
                solver.push()
                solver.add(boolean_expression)
                if check_sat(solver) == unsat:
                    solver.pop()
                    new_balance_is = global_state["balance"]["Is"] + transfer_amount
                    global_state["balance"]["Is"] = new_balance_is
                else:
                    solver.pop()
                    if isReal(recipient):
                        new_address_name = "concrete_address_" + str(recipient)
                    else:
                        new_address_name = gen.gen_arbitrary_address_var()
                    old_balance_name = gen.gen_arbitrary_var()
                    old_balance = BitVec(old_balance_name, 256)
                    path_conditions_and_vars[old_balance_name] = old_balance
                    constraint = old_balance >= 0
                    solver.add(constraint)
                    path_conditions_and_vars["path_condition"].append(constraint)
                    new_balance = old_balance + transfer_amount
                    global_state["balance"][new_address_name] = new_balance
        else:
            raise ValueError("STACK underflow")
    elif opcode == "CALLCODE":
        # TODO: Need to handle miu_i
        if len(stack) > 6:
            calls.append(global_state["pc"])
            for call_pc in calls:
                if call_pc not in calls_affect_state:
                    calls_affect_state[call_pc] = False
            global_state["pc"] = global_state["pc"] + 1
            outgas = stack.pop(0)
            recipient = stack.pop(0)  # this is not used as recipient

            transfer_amount = stack.pop(0)
            start_data_input = stack.pop(0)
            size_data_input = stack.pop(0)
            start_data_output = stack.pop(0)
            size_data_ouput = stack.pop(0)
            # in the paper, it is shaky when the size of data output is
            # min of stack[6] and the | o |

            if isReal(transfer_amount):
                if transfer_amount == 0:
                    stack.insert(0, 1)  # x = 0
                    return

            # Let us ignore the call depth
            balance_ia = global_state["balance"]["Ia"]
            is_enough_fund = transfer_amount <= balance_ia
            solver.push()
            solver.add(is_enough_fund)

            if check_sat(solver) == unsat:
                # this means not enough fund, thus the execution will result in exception
                solver.pop()
                stack.insert(0, 0)  # x = 0
            else:
                # the execution is possibly okay
                stack.insert(0, 1)  # x = 1
                solver.pop()
                solver.add(is_enough_fund)
                path_conditions_and_vars["path_condition"].append(is_enough_fund)
                last_idx = len(path_conditions_and_vars["path_condition"]) - 1
        else:
            raise ValueError("STACK underflow")
    elif opcode in ("DELEGATECALL", "STATICCALL"):
        if len(stack) > 5:
            global_state["pc"] += 1
            stack.pop(0)
            recipient = stack.pop(0)

            stack.pop(0)
            stack.pop(0)
            stack.pop(0)
            stack.pop(0)
            new_var_name = gen.gen_arbitrary_var()
            new_var = BitVec(new_var_name, 256)
            stack.insert(0, new_var)
        else:
            raise ValueError("STACK underflow")
    elif opcode in ("RETURN", "REVERT"):
        # TODO: Need to handle miu_i
        if len(stack) > 1:
            if opcode == "REVERT":
                revertible_overflow_pcs.update(overflow_pcs)
                global_state["pc"] = global_state["pc"] + 1
            stack.pop(0)
            stack.pop(0)
            # TODO
            pass
        else:
            raise ValueError("STACK underflow")
    elif opcode == "SELFDESTRUCT":
        global_state["pc"] = global_state["pc"] + 1
        recipient = stack.pop(0)
        transfer_amount = global_state["balance"]["Ia"]
        global_state["balance"]["Ia"] = 0
        if isReal(recipient):
            new_address_name = "concrete_address_" + str(recipient)
        else:
            new_address_name = gen.gen_arbitrary_address_var()
        old_balance_name = gen.gen_arbitrary_var()
        old_balance = BitVec(old_balance_name, 256)
        path_conditions_and_vars[old_balance_name] = old_balance
        constraint = old_balance >= 0
        solver.add(constraint)
        path_conditions_and_vars["path_condition"].append(constraint)
        new_balance = old_balance + transfer_amount
        global_state["balance"][new_address_name] = new_balance
        # TODO
        return

    # brand new opcodes
    elif opcode == "SHL":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            # *For selector to shift left 224 bits
            # EXP
            base = 2
            exponent = stack.pop(0)
            # Type conversion is needed when they are mismatched
            if isAllReal(base, exponent):
                computed = pow(base, exponent, 2**256)
            else:
                # The computed value is unknown, this is because power is
                # not supported in bit-vector theory
                new_var_name = gen.gen_arbitrary_var()
                computed = BitVec(new_var_name, 256)
            computed = simplify(computed) if is_expr(computed) else computed

            # MUL
            first = computed
            second = stack.pop(0)
            if isReal(first) and isSymbolic(second):
                first = BitVecVal(first, 256)
            elif isSymbolic(first) and isReal(second):
                second = BitVecVal(second, 256)
            computed = first * second & UNSIGNED_BOUND_NUMBER
            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
            if second == global_params.ONERC721RECEIVED_SELECTOR:
                global_params.ONERC721RECEIVED_SELECTOR_SHL = computed

            # *Simpler model
            # first = stack.pop(0)
            # second = stack.pop(0)
            # # Type conversion is needed when they are mismatched
            # if isReal(first) and isSymbolic(second):
            #     first = BitVecVal(first, 256)
            #     computed = first + second
            # elif isSymbolic(first) and isReal(second):
            #     second = BitVecVal(second, 256)
            #     computed = first + second
            # else:
            #     # both are real and we need to manually modulus with 2 ** 256
            #     # if both are symbolic z3 takes care of modulus automatically
            #     computed = mod((second + 2 ^ first), 2 ^ 256)

            # computed = simplify(computed) if is_expr(computed) else computed
            # stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")

    elif opcode == "SHR":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            # # EXP
            # base = 2
            # exponent = stack.pop(0)
            # # Type conversion is needed when they are mismatched
            # if isAllReal(base, exponent):
            #     computed = pow(base, exponent, 2**256)
            # else:
            #     # The computed value is unknown, this is because power is
            #     # not supported in bit-vector theory
            #     new_var_name = gen.gen_arbitrary_var()
            #     computed = BitVec(new_var_name, 256)
            # computed = simplify(computed) if is_expr(computed) else computed

            # # DIV
            # first = computed
            # second = stack.pop(0)
            # if isAllReal(first, second):
            #     if second == 0:
            #         computed = 0
            #     else:
            #         first = to_unsigned(first)
            #         second = to_unsigned(second)
            #         computed = first / second
            # else:
            #     first = to_symbolic(first)
            #     second = to_symbolic(second)
            #     solver.push()
            #     solver.add(Not(second == 0))
            #     if check_sat(solver) == unsat:
            #         computed = 0
            #     else:
            #         computed = UDiv(first, second)
            #     solver.pop()
            # computed = simplify(computed) if is_expr(computed) else computed
            # stack.insert(0, computed)

            # *Simpler model
            first = stack.pop(0)
            second = stack.pop(0)
            # Type conversion is needed when they are mismatched
            if isReal(first) and isSymbolic(second):
                first = BitVecVal(first, 256)
                computed = first + second
            elif isSymbolic(first) and isReal(second):
                second = BitVecVal(second, 256)
                computed = first + second
            else:
                # both are real and we need to manually modulus with 2 ** 256
                # if both are symbolic z3 takes care of modulus automatically
                computed = mod((second + 2 ^ first), 2 ^ 256)

            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")

    elif opcode == "SAR":
        if len(stack) > 1:
            global_state["pc"] = global_state["pc"] + 1
            # # EXP
            # base = 2
            # exponent = stack.pop(0)
            # # Type conversion is needed when they are mismatched
            # if isAllReal(base, exponent):
            #     computed = pow(base, exponent, 2**256)
            # else:
            #     # The computed value is unknown, this is because power is
            #     # not supported in bit-vector theory
            #     new_var_name = gen.gen_arbitrary_var()
            #     computed = BitVec(new_var_name, 256)
            # computed = simplify(computed) if is_expr(computed) else computed

            # # not equivalent to SDIV
            # first = computed
            # second = stack.pop(0)
            # if isAllReal(first, second):
            #     first = to_unsigned(first)
            #     second = to_signed(second)
            #     if second == 0:
            #         computed = 0
            #     elif first == -(2**255) and second == -1:
            #         computed = -(2**255)
            #     else:
            #         sign = -1 if (first / second) < 0 else 1
            #         computed = sign * (abs(first) / abs(second))
            # else:
            #     first = to_symbolic(first)
            #     second = to_symbolic(second)
            #     solver.push()
            #     solver.add(Not(second == 0))
            #     if check_sat(solver) == unsat:
            #         computed = 0
            #     else:
            #         solver.push()
            #         solver.add(Not(And(first == -(2**255), second == -1)))
            #         if check_sat(solver) == unsat:
            #             computed = -(2**255)
            #         else:
            #             solver.push()
            #             solver.add(first / second < 0)
            #             sign = -1 if check_sat(solver) == sat else 1

            #             def z3_abs(x):
            #                 return If(x >= 0, x, -x)

            #             first = z3_abs(first)
            #             second = z3_abs(second)
            #             computed = sign * (first / second)
            #             solver.pop()
            #         solver.pop()
            #     solver.pop()
            # computed = simplify(computed) if is_expr(computed) else computed
            # stack.insert(0, computed)

            # *Simpler model
            first = stack.pop(0)
            second = stack.pop(0)
            # Type conversion is needed when they are mismatched
            if isReal(first) and isSymbolic(second):
                first = BitVecVal(first, 256)
                computed = first + second
            elif isSymbolic(first) and isReal(second):
                second = BitVecVal(second, 256)
                computed = first + second
            else:
                # both are real and we need to manually modulus with 2 ** 256
                # if both are symbolic z3 takes care of modulus automatically
                computed = mod((second + 2 ^ first), 2 ^ 256)

            computed = simplify(computed) if is_expr(computed) else computed
            stack.insert(0, computed)
        else:
            raise ValueError("STACK underflow")

    elif opcode == "SELFBALANCE":
        # address(this).balance
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["currentSelfBalance"])

    elif opcode == "CHAINID":
        # chain_id = {  1 // mainnet
        #    {  2 // Morden testnet (disused)
        #    {  2 // Expanse mainnet
        #    {  3 // Ropsten testnet
        #    {  4 // Rinkeby testnet
        #    {  5 // Goerli testnet
        #    { 42 // Kovan testnet
        #    { ...
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["currentChainId"])

    elif opcode == "BASEFEE":
        global_state["pc"] = global_state["pc"] + 1
        stack.insert(0, global_state["currentBaseFee"])

    else:
        log.info("UNKNOWN INSTRUCTION: " + opcode)
        if global_params.UNIT_TEST == 2 or global_params.UNIT_TEST == 3:
            log.critical("Unknown instruction: %s" % opcode)
            exit(UNKNOWN_INSTRUCTION)
        raise Exception("UNKNOWN INSTRUCTION: " + opcode)


class TimeoutError(Exception):
    pass


class Timeout:
    """Timeout class using ALARM signal."""

    def __init__(self, sec=10, error_message=os.strerror(errno.ETIME)):
        self.sec = sec
        self.error_message = error_message

    def __enter__(self):
        signal.signal(signal.SIGALRM, self._handle_timeout)
        signal.alarm(self.sec)

    def __exit__(self, *args):
        signal.alarm(0)  # disable alarm

    def _handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)


def do_nothing():
    pass


def run_build_cfg_and_analyze(timeout_cb=do_nothing):
    initGlobalVars()
    global g_timeout
    try:
        with Timeout(sec=global_params.GLOBAL_TIMEOUT):
            build_cfg_and_analyze()
            log.debug("Done Symbolic execution")
    except TimeoutError:
        g_timeout = True
        timeout_cb()


def test():
    global_params.GLOBAL_TIMEOUT = global_params.GLOBAL_TIMEOUT_TEST

    def timeout_cb():
        traceback.print_exc()
        exit(EXCEPTION)

    run_build_cfg_and_analyze(timeout_cb=timeout_cb)


def analyze():
    def timeout_cb():
        if global_params.DEBUG_MODE:
            traceback.print_exc()

    run_build_cfg_and_analyze(timeout_cb=timeout_cb)


def run(disasm_file=None, source_file=None, source_map=None, slot_map=None):
    """Run specific contracts with the given sources and extracted slot map"""
    global g_disasm_file
    global g_source_file
    global g_src_map
    global results
    global begin
    global g_slot_map

    g_disasm_file = disasm_file
    g_source_file = source_file
    g_src_map = source_map
    g_slot_map = slot_map

    if is_testing_evm():
        test()
    else:
        begin = time.time()
        log.info("\t============ Results of %s===========" % source_map.cname)
        analyze()
        ret = Identifier.detect_defects(
            instructions,
            results,
            g_src_map,
            visited_pcs,
            global_problematic_pcs,
            begin,
            g_disasm_file,
        )
        return ret
    