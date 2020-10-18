import os
import subprocess
import shutil
from pathlib import Path

import lxml

from conf import config
from util import file_util, shell_util
from lxml import etree

ns = {"src": "http://www.srcML.org/srcML/src"}


def get_logging_calls_xml_of_repo(repo_path: str, repo_url: str, csv_path):
    file_list = file_util.get_all_java_kotlin_files(repo_path)
    keyword_list = file_util.get_keyword_list(csv_path, repo_url)
    result = []
    for file_path in file_list:
        str_file_path = str(file_path)
        logging_calls = get_logging_calls_xml_of_file(str_file_path, keyword_list)
        for call in logging_calls:
            result.append(call)

    return result


def get_logging_calls_xml_of_file(file_path: str, keyword_list):
    file_name, file_extension = os.path.splitext(file_path)
    temp_file_name = file_name.split('/')[-1]
    temp_file_path = file_path
    is_java_file = True
    if file_extension.lower() != '.java':
        temp_file_path = config.TEMP_FILE_PATH + temp_file_name + '.java'
        shutil.copy2(file_path, temp_file_path)
        is_java_file = False

    methods = get_methods_or_exprs_of_file(temp_file_path, is_java_file)
    if not is_java_file:
        os.remove(temp_file_path)
    result = []
    for method in methods:
        method_str = b'<root>' + etree.tostring(method) + b'</root>'
        parser = etree.XMLParser(huge_tree=True, encoding='utf-8', ns_clean=True, recover=True)
        method_xml = etree.fromstring(method_str, parser)
        logging_calls = get_logging_calls_xml_of_method(method_xml, keyword_list, is_java_file)
        for call in logging_calls:
            result.append(call)

    return result


def get_methods_or_exprs_of_file(file_path: str, is_java_file):
    xml_name = file_util.generate_random_file_name_with_extension('xml')
    methods = []
    xml_p = None
    try:
        shell_util.run_command("srcml '{}' -o {}".format(file_path, xml_name))
        xml_p = Path(xml_name)
        xml_bytes = xml_p.read_bytes()
        methods = get_methods_exprs_of_xml_bytes(xml_bytes, is_java_file)
    finally:
        xml_p.unlink()
        return methods


def get_methods_exprs_of_xml_bytes(xml_bytes, is_java_file):
    if xml_bytes is not None:
        parser = etree.XMLParser(huge_tree=True, encoding='utf-8', ns_clean=True, recover=True)
        try:
            xml_object = etree.fromstring(xml_bytes, parser=parser)
        except lxml.etree.XMLSyntaxError:
            print('Skipping invalid parsed XML object')
            return []

        if is_java_file:
            methods_or_exprs = xml_object.xpath('//src:unit//src:class[src:specifier]/src:block/src:function', namespaces=ns)
        else:
            methods_or_exprs = xml_object.xpath('//src:unit//src:expr', namespaces=ns)
        return methods_or_exprs
    else:
        return []


def get_logging_calls_xml_of_method(method_xml, keyword_list, is_java_file):
    result = []
    method_calls_xml = get_method_calls(method_xml, is_java_file)
    for method_call_xml in method_calls_xml:
        if _is_logging_call(method_call_xml, keyword_list):
            result.append(method_call_xml)

    # model_operator.save_logs_of_method_xml_str_if_needed(file_path, method_xml, result, repo_url, is_java_file)
    return result


def get_method_calls(method_xml, is_java_file):
    if is_java_file:
        # TODO: Get first call directly
        xpath_str = '//src:expr_stmt/src:expr/*[1]'
    else:
        xpath_str = './src:expr/*[1]'
    method_calls_xml = method_xml.xpath(xpath_str, namespaces=ns)
    result_method_calls_xml = method_calls_xml
    for item in method_calls_xml:
        if not etree.tostring(item).decode('utf-8').startswith('<call'):
            result_method_calls_xml.remove(item)
    return result_method_calls_xml


def _is_logging_call(method_call_xml, keyword_list):
    method_call_name = get_method_call_name(method_call_xml)

    if '.' in method_call_name:
        caller_name = method_call_name.split('.')[-1]
    else:
        caller_name = method_call_name

    if caller_name in keyword_list:
        return True

    return False


def get_method_call_name(method_call_xml):
    method_call_name = ''
    call_with_operator_xpath_str = 'src:name//*'
    call_without_operator_xpath_str = 'src:name'
    method_call_name_xml = method_call_xml.xpath(call_with_operator_xpath_str, namespaces=ns)
    if len(method_call_name_xml) == 0:
        method_call_name_xml = method_call_xml.xpath(call_without_operator_xpath_str, namespaces=ns)
    for item in method_call_name_xml:
        if item.text is not None:
            method_call_name += item.text
    return method_call_name


def transform_xml_str_to_code(xml_str):
    pre_str = config.XML_PRE_STRING
    xml_str = pre_str + xml_str + '</unit>'
    fifo_name = file_util.generate_random_file_name_with_extension('xml')
    os.mkfifo(fifo_name)

    try:
        process = subprocess.Popen(['srcml', fifo_name], stdout=subprocess.PIPE)
        with open(fifo_name, 'w') as f:
            f.write(xml_str)
        output = process.stdout.read()
    finally:
        os.remove(fifo_name)
    return str(output)[2:-1]


def get_method_full_signature(method_xml):
    signature = get_method_signature(method_xml)
    return signature[0] + signature[1]


def get_method_signature(method_xml):
    name_xpath = '//src:function/src:name'
    parameters_xpath = '//src:function/src:parameter_list/src:parameter/src:decl/src:type/src:name'
    parameters_element = method_xml.xpath(name_xpath, namespaces=ns)
    if parameters_element is not None and len(parameters_element) > 0:
        method_name = parameters_element[0]
        method_name_str = method_name.text
        parameters = method_xml.xpath(parameters_xpath, namespaces=ns)
        parameters_str = get_flatten_text_of_parameter(parameters)
        parameters_str = parameters_str[0:-1]
        parameters_str = '(' + parameters_str + ')'

        return method_name_str, parameters_str
    else:
        return '', ''


def get_flatten_text_of_parameter(xml):
    result = ''
    if not isinstance(xml, list):
        if len(xml) == 0:
            result = result + xml.text + ','
        else:
            for item in xml:
                result = result + get_flatten_text_of_parameter(item)
    else:
        for item in xml:
            result = result + get_flatten_text_of_parameter(item)
    return result


def get_methods_from_blob(file_blob, is_java_file):
    xml_bytes = get_xml_bytes_of_java(file_blob)
    methods = get_methods_exprs_of_xml_bytes(xml_bytes, is_java_file)
    return methods


def get_xml_bytes_of_java(file_blob):
    fifo_name = file_util.generate_random_file_name_with_extension('java')
    os.mkfifo(fifo_name)

    try:
        process = subprocess.Popen(['srcml', fifo_name], stdout=subprocess.PIPE)
        with open(fifo_name, 'wb') as f:
            f.write(file_blob.data_stream.read())
        output = process.stdout.read()
    finally:
        os.remove(fifo_name)

    return output


def get_logging_calls_from_blob(file_blob, is_java_file, keyword_list):
    xml_bytes = get_xml_bytes_of_java(file_blob)
    methods = get_methods_exprs_of_xml_bytes(xml_bytes, is_java_file)
    result = []
    for method in methods:
        method_str = b'<root>' + etree.tostring(method) + b'</root>'
        parser = etree.XMLParser(huge_tree=True, encoding='utf-8', ns_clean=True, recover=True)
        method_xml = etree.fromstring(method_str, parser)
        logging_calls = get_logging_calls_xml_of_method(method_xml, keyword_list, is_java_file)
        for call in logging_calls:
            result.append(call)

    return result






