import os
import shlex

import pandas as pd
import yaml
import click
from django.db import transaction

from catapult.models import File, ResultSummary, PrecursorReportContent, ProteinGroupReportContent

blank_diann_config = {'cat_file_auto': 'bool', 'cat_ready': 'bool', 'cat_total_files': 'number', 'channel_run_norm': 'bool', 'channel_spec_norm': 'bool', 'channels': 'list', 'clear_mods': 'bool', 'compact_report': 'bool', 'cont_quant_exclude': 'bool', 'convert': 'bool', 'cut': 'str', 'decoy_channel': 'str', 'decoys_preserve_spectrum': 'bool', 'diann_path': 'str', 'dir': 'str', 'direct_quant': 'bool', 'dl_no_im': 'bool', 'dl_no_rt': 'bool', 'duplicate_proteins': 'bool', 'exact_fdr': 'bool', 'export_quant': 'bool', 'ext': 'str', 'f': 'list', 'fasta': 'list', 'fasta_filter': 'str', 'fasta_search': 'bool', 'fixed_mod': 'list', 'force_swissprot': 'bool', 'foreign_decoys': 'bool', 'full_unimod': 'bool', 'gen_fr_restriction': 'bool', 'gen_spec_lib': 'bool', 'global_mass_cal': 'bool', 'global_norm': 'bool', 'high_acc': 'bool', 'ids_to_names': 'bool', 'il_eq': 'bool', 'im_window': 'str', 'im_window_factor': 'str', 'individual_mass_acc': 'bool', 'individual_reports': 'bool', 'individual_windows': 'bool', 'int_removal': 'str', 'lib': 'list', 'lib_fixed_mod': 'list', 'library_headers': 'list', 'mass_acc': 'number', 'mass_acc_cal': 'str', 'mass_acc_ms1': 'number', 'matrices': 'bool', 'matrix_ch_qvalue': 'str', 'matrix_qvalue': 'str', 'matrix_spec_q': 'bool', 'matrix_tr_qvalue': 'str', 'max_fr': 'str', 'max_fr_mz': 'number', 'max_pep_len': 'number', 'max_pr_charge': 'number', 'max_pr_mz': 'number', 'mbr_fix_settings': 'bool', 'met_excision': 'bool', 'min_fr': 'str', 'min_fr_mz': 'number', 'min_peak': 'str', 'min_pep_len': 'number', 'min_pr_charge': 'number', 'min_pr_mz': 'number', 'missed_cleavages': 'number', 'mod': 'list', 'mod_no_scoring': 'str', 'mod_only': 'bool', 'no_calibration': 'bool', 'no_cut_after_mod': 'str', 'no_decoy_channel': 'bool', 'no_fr_selection': 'bool', 'no_im_window': 'bool', 'no_isotopes': 'bool', 'no_lib_filter': 'bool', 'no_main_report': 'bool', 'no_maxlfq': 'bool', 'no_norm': 'bool', 'no_peptidoforms': 'bool', 'no_prot_inf': 'bool', 'no_quant_files': 'bool', 'no_rt_window': 'bool', 'no_stats': 'bool', 'no_swissprot': 'bool', 'original_mods': 'bool', 'out': 'str', 'out_lib': 'str', 'out_lib_copy': 'bool', 'out_measured_rt': 'bool', 'peak_translation': 'bool', 'peptidoforms': 'bool', 'pg_level': 'str', 'pr_filter': 'str', 'predict_n_frag': 'str', 'predictor': 'bool', 'prefix': 'str', 'ptm_qvalues': 'bool', 'quant_acc': 'str', 'quant_fr': 'str', 'quant_no_ms1': 'bool', 'quant_sel_runs': 'str', 'quant_train_runs': 'str', 'quick_mass_acc': 'bool', 'qvalue': 'number', 'reanalyse': 'bool', 'reannotate': 'bool', 'ref': 'str', 'regular_swath': 'bool', 'relaxed_prot_inf': 'bool', 'report_lib_info': 'bool', 'restrict_fr': 'bool', 'scanning_swath': 'bool', 'semi': 'bool', 'skip_unknown_mods': 'bool', 'smart_profiling': 'bool', 'species_genes': 'bool', 'species_ids': 'bool', 'sptxt_acc': 'str', 'tag_to_ids': 'str', 'temp': 'str', 'threads': 'number', 'tims_min_int': 'str', 'tims_ms1_cycle': 'str', 'tims_scan': 'bool', 'tims_skip_errors': 'bool', 'unimod': 'list', 'use_quant': 'bool', 'var_mod': 'list', 'var_mods': 'number', 'verbose': 'number', 'window': 'str', 'xic': 'str', 'xic_theoretical_fr': 'bool'}


def diann_yaml_parser(yaml_path):
    with open(yaml_path, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
            commands = [config["diann_path"]]
            for key, value in config.items():
                if key != "diann_path" and key !="ready":
                    key = key.replace("_", "-")
                    if value is not None:
                        if key == "channels":
                            if isinstance(value, list):
                                commands.append(f'--{key}')
                                commands.append("; ".join(value))
                            elif isinstance(value, str):
                                commands.append(f'--{key}')
                                commands.append(value)
                        elif isinstance(value, bool):
                            if value:
                                commands.append(f'--{key}')
                        elif isinstance(value, list):
                            if key == "unimod":
                                for item in value:
                                    commands.append(f'--unimod{str(item)}')
                            elif key == "temp":
                                commands.append(f'--temp')
                                commands.append(str(value))
                            elif key == "f":
                                for item in value:
                                    commands.append(f'--{key}')
                                    commands.append(str(item))
                            elif key == "out":
                                commands.append(f'--out')
                                commands.append(str(value))

                            else:
                                for item in value:
                                    commands.append(f'--{key}')
                                    commands.append(str(item))
                        else:
                            commands.append(f'--{key}')
                            commands.append(str(value))
            return " ".join(commands)
        except yaml.YAMLError as exc:
            print(exc)
            return None
def extract_cmd_from_diann_log(log_path):
    with open(log_path, 'rt') as log_file:
        for n, line in enumerate(log_file):
            if n == 6:
                return line.strip()

def convert_cmd_to_array(cmd):
    return shlex.split(cmd.replace("\\", "/"))

def convert_cmd_array_to_config(cmd_array: list[str]):
    # open the default config file as template
    commands_folder = os.path.join(os.path.dirname(__file__), "management", "commands")
    with open(os.path.join(commands_folder, "diann_config.cat.yml"), 'r') as stream:
        config = yaml.safe_load(stream)
    config["diann_path"] = cmd_array[0]
    for key, value in config.items():
        if key not in ["diann_path", "cat_ready", "cat_total_files", "cat_file_auto"]:
            cmd_key = key.replace("_", "-")
            if key == "temp":
                if "--temp" in cmd_array:
                    index = cmd_array.index("--temp")
                    config[key] = cmd_array[index+1]
                    config[key] = os.path.split(config[key])[1]
                else:
                    config[key] = None
            elif key == "out":
                if "--out" in cmd_array:
                    index = cmd_array.index("--out")
                    config[key] = cmd_array[index+1]
                    config[key] = os.path.split(config[key])[1]
                else:
                    config[key] = None
            if key == "out_lib":
                if "--out-lib" in cmd_array:
                    index = cmd_array.index("--out-lib")
                    config[key] = cmd_array[index+1]
                    config[key] = os.path.split(config[key])[1]
                else:
                    config[key] = None
            elif key == "channels":
                if f"--{cmd_key}" in cmd_array:
                    index = cmd_array.index(f"--{cmd_key}")
                    config[key] = cmd_array[index + 1].split(";")
                else:
                    config[key] = []
            elif key == "f":
                files = []
                for n, item in enumerate(cmd_array):
                    if item == "--f":
                        item_path = cmd_array[n + 1]
                        files.append(os.path.split(item_path)[1])

                config[key] = files
            elif key == "fasta":
                files = []
                for n, item in enumerate(cmd_array):
                    if item == "--fasta":
                        item_path = cmd_array[n + 1]
                        files.append(os.path.split(item_path)[1])

                config[key] = files
            elif key == "fixed_mod":
                files = []
                for n, item in enumerate(cmd_array):
                    if item == "--fixed-mod":
                        files.append(cmd_array[n + 1])

                config[key] = files
            elif key == "lib":
                files = []
                for n, item in enumerate(cmd_array):
                    if item == "--lib":
                        item_path = cmd_array[n + 1]
                        files.append(os.path.split(item_path)[1])

                config[key] = files
            elif key == "lib_fixed_mod":
                files = []
                for n, item in enumerate(cmd_array):
                    if item == "--lib-fixed-mod":
                        item_path = cmd_array[n + 1]
                        files.append(os.path.split(item_path)[1])

                config[key] = files
            elif key == "library_headers":
                files = []
                for n, item in enumerate(cmd_array):
                    if item == "--library-headers":
                        files.append(cmd_array[n + 1])
                        config[key] = files
            elif key == "mod":
                files = []
                for n, item in enumerate(cmd_array):
                    if item == "--mod":
                        files.append(cmd_array[n + 1])
                config[key] = files
            elif key == "var_mod":
                files = []
                for n, item in enumerate(cmd_array):
                    if item == "--var-mod":
                        files.append(cmd_array[n + 1])
                config[key] = files
            elif isinstance(value, bool):
                if f"--{cmd_key}" in cmd_array:
                    config[key] = True
                else:
                    config[key] = False
            elif isinstance(value, list):
                if key == "unimod":
                    unimods = [item for item in cmd_array if item.startswith("--unimod")]
                    if unimods:
                        config[key] = [int(item[8:]) for item in unimods]
                    else:
                        config[key] = []

            elif isinstance(value, str):
                if f"--{cmd_key}" in cmd_array:
                    index = cmd_array.index(f"--{cmd_key}")
                    config[key] = cmd_array[index+1]
                else:
                    config[key] = None
    if len(config["f"]) > 0:
        config["cat_total_files"] = len(config["f"])
    return config

@click.command()
@click.option("--yaml_path", "-y", help="Path to the yaml file")
def main(yaml_path):
    print(diann_yaml_parser(yaml_path))

if __name__ == "__main__":
    main()


def add_stats_and_report(analysis, config, parent_folder, report_stats_file):
    if os.path.exists(report_stats_file):
        data = pd.read_csv(str(report_stats_file), sep="\t")
        for i, r in data.iterrows():
            file_path = r["File.Name"].replace(config.folder_watching_location.folder_path,
                                               "")
            file = File.objects.get(file_path=file_path)
            result_summary = ResultSummary.objects.filter(analysis=analysis, file=file)
            if not result_summary.exists():
                result_summary = ResultSummary.objects.create(
                    analysis=analysis,
                    file=file,
                    protein_identified=r["Proteins.Identified"],
                    precursor_identified=r["Precursors.Identified"],
                    stats_file=os.path.join(
                        str(parent_folder.replace(config.folder_watching_location.folder_path, "")),
                        config.content["prefix"],
                        "report.stats.tsv"
                    ),
                    log_file=os.path.join(
                        str(parent_folder.replace(config.folder_watching_location.folder_path, "")),
                        config.content["prefix"],
                        "report.log.txt"
                    )
                )
            else:
                result_summary = result_summary.first()
                if r["Proteins.Identified"] != result_summary.protein_identified or r[
                    "Precursors.Identified"] != result_summary.precursor_identified:
                    result_summary.protein_identified = r["Proteins.Identified"]
                    result_summary.precursor_identified = r["Precursors.Identified"]
                    result_summary.stats_file = os.path.join(
                        str(parent_folder.replace(config.folder_watching_location.folder_path, "")),
                        config.content["prefix"],
                        "report.stats.tsv"
                    )
                    result_summary.save()
            result_summary.precursor_report_content.all().delete()
            result_summary.protein_group_report_content.all().delete()
            file_obj = File.objects.get(file_path=file_path)
            precursor_file = pd.read_csv(
                str(os.path.join(parent_folder, config.content["prefix"], "report.pr_matrix.tsv")), sep="\t")
            with transaction.atomic():
                filtered_precursor_file = precursor_file[pd.notnull(precursor_file[r["File.Name"]])]
                data = [
                    PrecursorReportContent(
                        file=file_obj,
                        proteotypic=row["Proteotypic"] == 1,
                        protein_group=row["Protein.Group"],
                        intensity=row[r["File.Name"]],
                        gene_names=row["Genes"],
                        precursor_id=row["Precursor.Id"],
                        result_summary=result_summary
                    )
                    for _, row in filtered_precursor_file.iterrows()
                ]
                if len(data) > 0:
                    PrecursorReportContent.objects.bulk_create(data)
            protein_file = pd.read_csv(
                str(os.path.join(parent_folder, config.content["prefix"], "report.pg_matrix.tsv")), sep="\t")
            with transaction.atomic():
                filtered_protein_file = protein_file[pd.notnull(protein_file[r["File.Name"]])]

                data = [
                    ProteinGroupReportContent(
                        file=file_obj,
                        protein_group=row["Protein.Group"],
                        intensity=row[r["File.Name"]],
                        gene_names=row["Genes"],
                        result_summary=result_summary
                    )
                    for _, row in filtered_protein_file.iterrows()
                ]

                if len(data) > 0:
                    ProteinGroupReportContent.objects.bulk_create(data)

def load_diann_default_confg():
    commands_folder = os.path.join(os.path.dirname(__file__), "management", "commands")
    with open(os.path.join(commands_folder, "diann_config.cat.yml"), 'r') as stream:
        config = yaml.safe_load(stream)
    return config
