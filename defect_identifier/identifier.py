import time
import global_params
import json
import logging
from rich.console import Console
from rich.table import Table
from defect_identifier.defect import (
    PublicBurnDefect,
    ReentrancyDefect,
    RiskyProxyDefect,
    UnlimitedMintingDefect,
    ViolationDefect,
    PrivilegedAddressDefect,
    UnrestrictedFromDefect,
    EmptyTransferEventDefect,
)

log = logging.getLogger(__name__)


class Identifier:
    @classmethod
    def detect_defects(
        self,
        instructions,
        results,
        g_src_map,
        visited_pcs,
        global_problematic_pcs,
        begin,
        g_disasm_file,
    ):
        """Analyzes defects and reports the final results."""
        if instructions:
            evm_code_coverage = float(len(visited_pcs)) / len(instructions.keys()) * 100
            results["evm_code_coverage"] = str(round(evm_code_coverage, 1))
            results["instructions"] = str(len(instructions.keys()))

            end = time.time()

            # *All Defects to be detectd...
            # self.detect_violation(self, results, g_src_map, global_problematic_pcs)
            # self.detect_reentrancy(self, results, g_src_map, global_problematic_pcs)
            # self.detect_proxy(self, results, g_src_map, global_problematic_pcs)
            # self.detect_unlimited_minting(
            #     self, results, g_src_map, global_problematic_pcs
            # )
            # self.detect_public_burn(self, results, g_src_map, global_problematic_pcs)
            global pa
            global uf
            global ete
            pa = PrivilegedAddressDefect(results["analysis"]["privileged_address"])
            uf = UnrestrictedFromDefect(results["analysis"]["unrestricted_from_and_owner_inconsistency"])
            ete = EmptyTransferEventDefect(results["analysis"]["empty_transfer_event"])

            defect_table = Table()

            defect_table.add_column(
                "Defect", justify="right", style="dim", no_wrap=True
            )
            defect_table.add_column("Status", style="green")
            defect_table.add_column("Location", justify="left", style="cyan")

            defect_table.add_row(
                "Privileged Address\n", str(pa.is_defective()), str(pa)
            )
            defect_table.add_row(
                "Unrestricted 'from'/\nOwner Inconsistency\n", str(uf.is_defective()), str(uf)
            )
            defect_table.add_row(
                "Empty Transfer Event",
                str(ete.is_defective()),
                str(ete),
            )

            param_table = Table()
            param_table.add_column("Time", justify="left", style="cyan", no_wrap=True)
            param_table.add_column(
                "Code Coverage", justify="left", style="yellow", no_wrap=True
            )
            param_table.add_row(
                str(round(end - begin, 1)), str(round(evm_code_coverage, 1))
            )

            instruct = Table()
            instruct.add_column(
                "Total Instructions",
                justify="left",
                style="cyan",
                no_wrap=True,
                width=20,
            )

            instruct.add_row(results["instructions"])

            state_table = Table.grid(expand=True)
            state_table.add_column(justify="center")
            state_table.add_row(param_table)
            state_table.add_row(instruct)

            reporter = Table(title="WakeMint GENESIS v0.0.1")
            reporter.add_column("Defect Detection", justify="center")
            reporter.add_column("Execution States", justify="center")
            reporter.add_row(defect_table, state_table)

            console = Console()
            console.print(reporter)

        else:
            log.info("\t  No Instructions \t")
            results["evm_code_coverage"] = "0/0"
        self.closing_message(begin, g_disasm_file, results, end)
        return results, self.defect_found(g_src_map)

    def detect_violation(self, results, g_src_map, global_problematic_pcs):
        global violation

        pcs = global_problematic_pcs["violation_defect"]
        violation = ViolationDefect(g_src_map, pcs)

        if g_src_map:
            results["analysis"]["violation"] = violation.get_warnings()
        else:
            results["analysis"]["violation"] = violation.is_defective()
        results["bool_defect"]["violation"] = violation.is_defective()

    def detect_reentrancy(self, results, g_src_map, global_problematic_pcs):
        global reentrancy

        pcs = global_problematic_pcs["reentrancy_defect"]
        reentrancy = ReentrancyDefect(g_src_map, pcs)

        if g_src_map:
            results["analysis"]["reentrancy"] = reentrancy.get_warnings()
        else:
            results["analysis"]["reentrancy"] = reentrancy.is_defective()
        results["bool_defect"]["reentrancy"] = reentrancy.is_defective()

    def detect_proxy(self, results, g_src_map, global_problematic_pcs):
        global proxy

        pcs = global_problematic_pcs["proxy_defect"]
        proxy = RiskyProxyDefect(g_src_map, pcs)

        if g_src_map:
            results["analysis"]["proxy"] = proxy.get_warnings()
        else:
            results["analysis"]["proxy"] = proxy.is_defective()
        results["bool_defect"]["proxy"] = proxy.is_defective()

    def detect_unlimited_minting(self, results, g_src_map, global_problematic_pcs):
        global unlimited_minting

        pcs = global_problematic_pcs["unlimited_minting_defect"]
        unlimited_minting = UnlimitedMintingDefect(g_src_map, pcs)

        if g_src_map:
            results["analysis"]["unlimited_minting"] = unlimited_minting.get_warnings()
        else:
            results["analysis"]["unlimited_minting"] = unlimited_minting.is_defective()
        results["bool_defect"]["unlimited_minting"] = unlimited_minting.is_defective()

    def detect_public_burn(self, results, g_src_map, global_problematic_pcs):
        global public_burn

        pcs = global_problematic_pcs["burn_defect"]
        public_burn = PublicBurnDefect(g_src_map, pcs)

        if g_src_map:
            results["analysis"]["burn"] = public_burn.get_warnings()
        else:
            results["analysis"]["burn"] = public_burn.is_defective()
        results["bool_defect"]["burn"] = public_burn.is_defective()

    def log_info():
        global pa
        global uf
        global ete

        defects = [pa, uf, ete]

        for defect in defects:
            s = str(defect)
            if s:
                log.info(s)

    def defect_found(g_src_map):
        global pa
        global uf
        global ete

        defects = [pa, uf, ete]

        for defect in defects:
            if defect.is_defective():
                return 1
        return 0

    def closing_message(begin, g_disasm_file, results, end):
        results["time"] = str(end - begin)
        # write down extra contract info...
        results["address"] = global_params.CONTRACT_ADDRESS
        results["contract_count"] = global_params.CONTRACT_COUNT
        results["storage_var_count"] = global_params.STORAGE_VAR_COUNT
        results["pub_fun_count"] = global_params.PUB_FUN_COUNT

        log.info("\t====== Analysis Completed ======")
        if global_params.STORE_RESULT:
            result_file = g_disasm_file.split(".evm.disasm")[0] + ".json"
            with open(result_file, "w") as of:
                of.write(json.dumps(results, indent=1))
            log.info("Wrote results to %s.", result_file)
