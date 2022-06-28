import pandas as pd
import numpy as np
from datetime import date
import glob
import os
import ipysheet


# NMD File functions:
def extract_string_for_tag(string, tag):
    i = string.find('<' + tag)
    f = string.find('</' + tag + '>')
    if f < 0:
        f = string.find('/>')
        end_tag_len = 2
    else:
        end_tag_len = 3 + len(tag)
    return string[i:f], f + end_tag_len


def convert_value(value):
    value = value.strip()
    if len(value) == 0:
        return value
    elif value[0] in ['"', "'"] and value[-1] in ['"', "'"] and value[0] == value[-1]:
        value = value[1:-1]
    for convert_func in [int, float]:
        try:
            value = convert_func(value)
        except:
            pass
        else:
            return value

    return value


def parse_parametets(parameter_list):
    result = {}
    key = 'content'
    for parameter in parameter_list:
        if '=' in parameter:
            key = parameter.split('=')[0]
            value = "=".join(parameter.split('=')[1:])
            result[key] = convert_value(value)
        elif key not in result:
            result[key] = parameter
        else:
            result[key] += " " + parameter
    return result


def parse_tag(string, tag):
    open_i = string[1:].find('<')
    close_i = string[1:].find('>')
    close_direct = string[1:].find('/>')
    result = {}
    if open_i < close_i:
        raise ValueError
    if close_direct <= close_i:
        result = {"Parameters": parse_parametets(string[len(tag) + 1:-2].split())}
    else:
        result["Parameters"] = parse_parametets(string[len(tag) + 1: close_i + 1].split())
        content_string = string[close_i + 2:]
        while content_string.startswith('<'):
            new_tag = content_string[1:].split()[0]
            _i = new_tag.find('>')
            _f = new_tag.find('<')
            if _i > 1 and _i < _f:
                new_tag = new_tag[:_i]
            # print(f"new tag = {new_tag}")
            new_tag_string, char_number = extract_string_for_tag(content_string, new_tag)
            # print(f"new tag string {new_tag_string}")
            result[new_tag] = parse_tag(new_tag_string, new_tag)
            content_string = content_string[char_number:]
        if len(content_string) > 0:
            result["Content"] = content_string

    return result


def parse_tiff_metadata(tiff_img):
    result = []
    for key, val in tiff_img.tag_v2.items():
        if isinstance(val, str):
            result.append(val)

    result_2 = {'None': {}}
    key = 'None'

    for str_entry in result:
        for line in str_entry.replace('\r', '').split('\n'):
            if len(line) > 2 and line[0] == '[' and line[-1] == ']':
                key = line[1:-1]
                result_2[key] = {}
            else:
                sub_key = line.split('=')[0]
                value = '='.join(line.split('=')[1:])
                result_2[key][sub_key] = value

    if isinstance(result_2['None'], dict) and len(result_2['None']) == 0:
        del result_2['None']
    for val in result_2.values():
        if isinstance(val, dict) and '' in val and val[''] == '':
            del val['']
    return result_2


def parse_nmd(file_name):
    with open(file_name, 'rb') as f:
        string = f.read()
    full_string = string[string.find(b'<SAMPLE'):string.find(b'</SAMPLE>') + len('</SAMPLE>')].decode()
    result = {}
    w_string, f = extract_string_for_tag(full_string, 'SAMPLE')
    result['SAMPLE'] = parse_tag(w_string, 'SAMPLE')
    return result


class NanoIndForm:
    _result_xls_form_map = {
        'Target  Depth': 'Target depth [nm]',
        'Target  Load': 'Target load [mN]',
        'Depth To Start Ave.': 'Start of averaging depth [nm]',
        'Depth To End Ave.': 'End of averaging depth [nm]',
        'YYYY_MM_DD': 'Measurement date',
        'Hold Maximum Load Time': 'Hold time at maximum load [s]',
        'RelHumidity': 'Relative humidity [%]',
        'EnvironmentalGas': 'Environmental gas',
        'MeasurementPos': 'Measurement position',
        'Temperature': 'Temperature [°C]',
        'Target Ind. Strain Rate': 'Target strain rate [/s]',
        # :'Target displacement rate [nm/s]'  # either this or ^
    }
    _nano_ind_scheme = {'ID': {'required': True, 'options': []},
                        'External/alias ID': {'required': False, 'options': []},
                        'User': {'required': True, 'options': []},
                        'Date': {'required': True, 'options': []},
                        'Affiliation': {'required': False, 'options': []},
                        'DOIs': {'required': False, 'options': []},
                        'Temperature [°C]': {'required': False, 'options': []},
                        'Relative humidity [%]': {'required': False, 'options': []},
                        'Environmental gas': {'required': False, 'options': []},
                        'Operator': {'required': False, 'options': []},
                        'Instrument ID': {'required': False, 'options': []},
                        'Sample ID': {'required': False, 'options': []},
                        'Parent sample ID': {'required': False, 'options': []},
                        'Any data set to be linked with this experiment': {'required': False,
                                                                           'options': []},
                        'Environmental protection during sample processing': {'required': False,
                                                                              'options': []},
                        'Pre-treatment': {'required': False, 'options': []},
                        'Measurement position': {'required': False, 'options': []},
                        'Sample orientation': {'required': False, 'options': []},
                        'Type of test': {'required': False, 'options': []},
                        'Control method': {'required': False, 'options': []},
                        'Tip ID': {'required': False, 'options': []},
                        'Diamond area function': {'required': False, 'options': []},
                        'Date of calibration': {'required': False, 'options': []},
                        'Frame stiffness [N/m]': {'required': False, 'options': []},
                        'Target load [mN]': {'required': False, 'options': []},
                        'Target depth [nm]': {'required': False, 'options': []},
                        'Continuous stiffness measurement': {'required': False, 'options': []},
                        'Drift correction enabled': {'required': False, 'options': []},
                        'Sample temperature [°C]': {'required': False, 'options': []},
                        'Tip temperature [°C]': {'required': False, 'options': []},
                        'Target strain rate [/s]': {'required': False, 'options': []},
                        'Target loading rate [mN/s]': {'required': False, 'options': []},
                        'Target displacement rate [nm/s]': {'required': False, 'options': []},
                        'Start of averaging depth [nm]': {'required': False, 'options': []},
                        'End of averaging depth [nm]': {'required': False, 'options': []},
                        'Hold time at maximum load [s]': {'required': False, 'options': []},
                        'Measurement date': {'required': False, 'options': []},
                        'Comments': {'required': False, 'options': []}}

    def __init__(self):
        self.nmd_dict = None
        self._xls_file = None
        for key, value in self._nano_ind_scheme.items():
            value['value'] = None

    def __getitem__(self, item):
        if item not in self.keys():
            raise KeyError(item)
        return self._nano_ind_scheme[item]['value']

    def __setitem__(self, item, value):
        if item not in self.keys():
            raise KeyError(item)
        self._nano_ind_scheme[item]['value'] = value

    def keys(self):
        return self._nano_ind_scheme.keys()

    def to_dict(self):
        return {key: self._nano_ind_scheme[key]['value'] for key in self._nano_ind_scheme}

    def items(self):
        return self.to_dict().items()

    def parse_xls_file(self, xls_file, row_name=1):
        self._xls_file = pd.ExcelFile(xls_file)
        result_sheet = pd.read_excel(self._xls_file, sheet_name='Results', header=[0, 1])
        mask = (result_sheet['Test'] == row_name).values
        result_sheet = result_sheet[mask]
        for key, own_key in self._result_xls_form_map.items():
            try:
                res = result_sheet[key].values[0, 0]
                if res == "0" or res == 0:
                    res = None
                self[own_key] = res
            except KeyError:
                self[own_key] = None

        m_date = self['Measurement date']
        if isinstance(m_date, (int, str, np.int64)):
            year = int(str(m_date)[0:4])
            month = int(str(m_date)[4:6])
            day = int(str(m_date)[6:])
            self['Measurement date'] = date(year, month, day)

    def parse_nmd(self, nmd_file):
        self.nmd_dict = parse_nmd(nmd_file)
        machine_config_dict = self.nmd_dict['SAMPLE']['MACHINECONFIG']["Parameters"]
        self['Frame stiffness [N/m]'] = machine_config_dict['FRAMESTIFFNESS']
        self['Diamond area function'] = self._parse_area_coeffs(machine_config_dict)
        print(machine_config_dict.keys())

    @staticmethod
    def _parse_area_coeffs(machine_config_dict):
        result = ""
        n_coeff = machine_config_dict['AREACOEFFS']
        for i in range(n_coeff):
            key = f"AREACOEFF{i}"
            result += f"{machine_config_dict[key]}x**{i} +"
        return result

    def __repr__(self):
        result = "Meta data scheme:    Nanoindentation \n"
        result += 100 * "=" + '\n'
        for key, value in self.items():
            result += f"{key}".ljust(50) + f"  =  {value} ".ljust(50) + "\n"
        return result
