import ast
import json

import six

import global_params
from cfg_builder.utils import run_command
from inputter.ast.ast_helper import AstHelper
from inputter.slot_map import SlotMap


class Source:
    def __init__(self, filename):
        self.filename = filename
        self.content = self._load_content()
        self.line_break_positions = self._load_line_break_positions()

    def _load_content(self):
        with open(self.filename, "rb") as f:
            content = f.read().decode("UTF-8")
        return content

    def _load_line_break_positions(self):
        return [i for i, letter in enumerate(self.content) if letter == "\n"]


class SourceMap:
    parent_filename = ""
    position_groups = {}
    sources = {}
    ast_helper = None
    slot_map = None
    func_to_sig_by_contract = {}

    def __init__(self, cname, parent_filename, remap, input_type, root_path=""):
        self.root_path = root_path
        self.cname = cname
        self.input_type = input_type
        self.remap = remap
        if not SourceMap.parent_filename:
            SourceMap.parent_filename = parent_filename
            if input_type == "solidity":
                SourceMap.position_groups = SourceMap._load_position_groups(remap)
            else:
                # TODO add more type of inputter
                raise Exception("There is no such type of inputter")
            SourceMap.ast_helper = AstHelper(
                SourceMap.parent_filename, remap, input_type
            )
            SourceMap.slot_map = SlotMap(cname, parent_filename, remap)
            SourceMap.func_to_sig_by_contract = SourceMap._get_sig_to_func_by_contract(
                remap
            )
        self.source = self._get_source()
        self.positions = self._get_positions()
        self.instr_positions = {}
        self.var_names = self._get_var_names()
        # mark state variable counts
        global_params.STORAGE_VAR_COUNT = len(self.var_names)
        self.safe_func_call_info = self._get_safe_func_calls()
        self.func_call_names = self._get_func_call_names()

        self.callee_src_pairs = self._get_callee_src_pairs()
        self.func_name_to_params = self._get_func_name_to_params()
        self.sig_to_func = self._get_sig_to_func()

        # mark public function counts
        global_params.PUB_FUN_COUNT = len(self.sig_to_func.keys())

    def get_source_code(self, pc):
        try:
            pos = self.instr_positions[pc]
        except:
            return ""
        begin = pos["begin"]
        end = pos["end"]
        return self.source.content[begin:end]

    def get_source_code_from_src(self, src):
        src = src.split(":")
        start = int(src[0])
        end = start + int(src[1])
        return self.source.content[start:end]

    def get_buggy_line(self, pc):
        try:
            pos = self.instr_positions[pc]
        except:
            return ""
        location = self.get_location(pc)
        begin = self.source.line_break_positions[location["begin"]["line"] - 1] + 1
        end = pos["end"]
        return self.source.content[begin:end]

    def get_buggy_line_from_src(self, src):
        pos = self._convert_src_to_pos(src)
        location = self.get_location_from_src(src)
        begin = self.source.line_break_positions[location["begin"]["line"] - 1] + 1
        end = pos["end"]
        return self.source.content[begin:end]

    def get_location(self, pc):
        pos = self.instr_positions[pc]
        return self._convert_offset_to_line_column(pos)

    def _get_max_code_line(self):
        pos = self.instr_positions[self.end_pc]
        return self._convert_offset_to_line_column(pos)

    def get_location_from_src(self, src):
        pos = self._convert_src_to_pos(src)
        return self._convert_offset_to_line_column(pos)

    def get_parameter_or_state_var(self, var_name):
        try:
            names = [
                node.id
                for node in ast.walk(ast.parse(var_name))
                if isinstance(node, ast.Name)
            ]
            if names[0] in self.var_names:
                return var_name
        except:
            return None
        return None

    def _convert_src_to_pos(self, src):
        pos = {}
        src = src.split(":")
        pos["begin"] = int(src[0])
        length = int(src[1])
        pos["end"] = pos["begin"] + length - 1
        return pos

    def _get_sig_to_func(self):
        func_to_sig = SourceMap.func_to_sig_by_contract[self.cname]["hashes"]
        return dict((sig, func) for func, sig in six.iteritems(func_to_sig))

    def _get_func_name_to_params(self):
        func_name_to_params = SourceMap.ast_helper.get_func_name_to_params(self.cname)
        for func_name in func_name_to_params:
            calldataload_position = 0
            for param in func_name_to_params[func_name]:
                if param["type"] == "ArrayTypeName":
                    param["position"] = calldataload_position
                    calldataload_position += param["value"]
                else:
                    param["position"] = calldataload_position
                    calldataload_position += 1
        return func_name_to_params

    def _get_source(self):
        fname = self.get_filename()
        if fname not in SourceMap.sources:
            SourceMap.sources[fname] = Source(fname)
        return SourceMap.sources[fname]

    def _get_callee_src_pairs(self):
        return SourceMap.ast_helper.get_callee_src_pairs(self.cname)

    def _get_var_names(self):
        return SourceMap.ast_helper.extract_state_variable_names(self.cname)

    def _get_func_call_names(self):
        func_call_srcs = SourceMap.ast_helper.extract_func_call_srcs(self.cname)
        func_call_names = []
        for src in func_call_srcs:
            src = src.split(":")
            start = int(src[0])
            end = start + int(src[1])
            func_call_names.append(self.source.content[start:end])
        return func_call_names

    def _get_safe_func_calls(self):
        safe_func_call_info = SourceMap.ast_helper.extract_safe_func_call_info(
            self.cname
        )
        locations = []
        for info in safe_func_call_info:
            for key in info:
                locations.append((self.get_location_from_src(key), info[key]))
        return locations

    @classmethod
    def _get_sig_to_func_by_contract(cls, remap):
        cmd = "solc --combined-json hashes %s %s" % (
            cls.parent_filename,
            " ".join(remap),
        )
        out = run_command(cmd)
        out = json.loads(out)
        return out["contracts"]

    @classmethod
    def _load_position_groups(cls, remap):
        cmd = "solc --combined-json asm %s %s" % (
            cls.parent_filename,
            " ".join(remap),
        )
        
        out = run_command(cmd)
        out = json.loads(out)
        # with open("try.json", "w", encoding="utf-8") as f:
        #     f.write(json.dumps(out))
        return out["contracts"]

    def _get_positions(self):
        if self.input_type == "solidity":
            # for different relative path (in the project or outside directory)
            # self.cname = self.cname.replace("/path1", "/path2")
            # try:
            asm = SourceMap.position_groups[self.cname]["asm"][".data"]["0"]
            # except:
            # return None
        else:
            filename, contract_name = self.cname.split(":")
            asm = SourceMap.position_groups[filename][contract_name]["evm"][
                "legacyAssembly"
            ][".data"]["0"]
        positions = asm[".code"]
        while True:
            try:
                positions.append(None)
                positions += asm[".data"]["0"][".code"]
                asm = asm[".data"]["0"]
            except:
                break
        return positions

    def _convert_offset_to_line_column(self, pos):
        ret = {}
        ret["begin"] = None
        ret["end"] = None
        if pos["begin"] >= 0 and (pos["end"] - pos["begin"] + 1) >= 0:
            ret["begin"] = self._convert_from_char_pos(pos["begin"])
            ret["end"] = self._convert_from_char_pos(pos["end"])
        return ret

    def _convert_from_char_pos(self, pos):
        line = self._find_lower_bound(pos, self.source.line_break_positions)
        if self.source.line_break_positions[line] != pos:
            line += 1
        begin_col = 0 if line == 0 else self.source.line_break_positions[line - 1] + 1
        col = pos - begin_col
        return {"line": line, "column": col}

    def _find_lower_bound(self, target, array):
        start = 0
        length = len(array)
        while length > 0:
            half = length >> 1
            middle = start + half
            if array[middle] <= target:
                length = length - 1 - half
                start = middle + 1
            else:
                length = half
        return start - 1

    def get_filename(self):
        return self.cname.split(":")[0]
