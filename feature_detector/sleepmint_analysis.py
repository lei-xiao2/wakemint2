from z3 import *
import re
TRANSFER_EVENT_HASH = 100389287136786176327247604509743168900146139575972864366142685224231313322991

def sleepmint_analysis(opcode, stack, solver, _from, owner, test_results, sstore_mark, current_func):
    if opcode == "LOG4" and stack[2] == TRANSFER_EVENT_HASH:
        if not sstore_mark:
            test_results[2][0] = 1
            temp = current_func + ":standard1"
            if temp not in test_results[2]:
                test_results[2].append(temp)
            return
        # if stack[3] == 0:
        #     to = stack[4]
        #     bvs = []
        #     for arg in to.children():
        #         children = arg.children()
        #         if children == [] and not is_bv_value(arg):
        #             bvs.append(arg.decl().name())
        #         else:
        #             while len(children):
        #                 item = children.pop(0)
        #                 if item.children():
        #                     children += item.children()
        #                 elif not is_bv_value(item):
        #                     bvs.append(item.decl().name())
        #     for bv in bvs:
        #         if re.match("Id_[\d]+", bv) or "Is" in bv:
        #             return
                
        #     test_results[2][0] = 1
        #     temp = current_func + ":standard2"
        #     if temp not in test_results[2]:
        #         test_results[2].append(temp)
        #     return
        
        for assertion in solver.assertions():
            q = [assertion]
            while len(q) != 0:
                cur = q.pop(0)
                if cur.decl().kind() == Z3_OP_EQ:
                    bvs = []
                    for arg in cur.children():
                        children = arg.children()
                        if children == [] and not is_bv_value(arg):
                            bvs.append(arg.decl().name())
                        else:
                            while len(children):
                                item = children.pop(0)
                                if item.children():
                                    children += item.children()
                                elif not is_bv_value(item):
                                    bvs.append(item.decl().name())
                    if "Is" in bvs:
                        other_var = bvs[0] if bvs[0] != "Is" else bvs[1]
                        pattern = "\[[\w\d_]+\]"
                        match = re.search(pattern, other_var)
                        if other_var.startswith("Ia_store") and not match:
                            test_results[1][0] = 1
                            temp = current_func + ":" + other_var
                            if temp not in test_results[1]:
                                test_results[1].append(temp)
                else:
                    for arg in cur.children():
                        q.append(arg)

        if "(address,address,uint256)" in current_func or "(address, address, uint256)" in current_func:
            expr = If(Extract(159, 0, _from) != Extract(159, 0, owner), 1, 0) != 0
            solver.push()
            solver.add(expr)

            if solver.check() == unsat:
                pass
            else:
                test_results[0][0] = 1
                if current_func not in test_results[0]:
                    test_results[0].append(current_func)
            solver.pop()