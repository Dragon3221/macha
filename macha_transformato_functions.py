#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 25 15:50:05 2022

@author: Johannes Karwanoupoulos and Åsmund Kaupang
"""
import sys
import os
import glob
import shutil
import subprocess
import parmed as pm
import pandas as pd
import logging

################################################################################
### FUNCTIONS
################################################################################
# HET BLOCK GENERATION
################################################################################
def genPROblock(protein_id, segment_id="PROA"):

    block = (
        f"!-------------------------------------------------------------------------------\n"
        f"! PROTEIN:\n"
        f"open read card unit 10 name {protein_id.lower()}_{segment_id.lower()}.crd\n"
        f"read sequence coor card unit 10 resid\n"
        f"generate {segment_id.upper()} setup warn first NTER last CTER\n"
        f"\n"
        f"open read unit 10 card name {protein_id.lower()}_{segment_id.lower()}.crd\n"
        f"read coor unit 10 card resid\n"
        f"!-------------------------------------------------------------------------------\n"
    )

    return block


def genHETblock(ligand_id, segment_id="HETA"):

    block = (
        f"!-------------------------------------------------------------------------------\n"
        f"open read card unit 10 name {ligand_id.lower()}.crd\n"
        f"read sequence coor card unit 10 resid\n"
        f"generate {segment_id.upper()} setup warn first none last none\n"
        f"\n"
        f"open read unit 10 card name {ligand_id.lower()}.crd\n"
        f"read coor unit 10 card resid\n"
        f"!-------------------------------------------------------------------------------\n"
    )

    return block


def genWATblock(protein_id, segment_id="WATA"):

    block = (
        f"!-------------------------------------------------------------------------------\n"
        f"open read card unit 10 name {protein_id.lower()}_{segment_id.lower()}.crd\n"
        f"read sequence coor card unit 10 resid\n"
        f"generate {segment_id.upper()} setup warn noangle nodihedral\n"
        f"\n"
        f"open read unit 10 card name {protein_id.lower()}_{segment_id.lower()}.crd\n"
        f"read coor unit 10 card resid\n"
        f"!-------------------------------------------------------------------------------\n"
    )

    return block


################################################################################
# HBUILD CONTROL
################################################################################
def hbuild_preserve_explicit_H(segids):

    segid_head = f"hbuild sele hydr .and. .not. ("
    segid_vars = ""
    for idx, segid in enumerate(segids):
        if idx == len(segids) - 1:
            segid_add = f"segid {segid}"
        else:
            segid_add = f"segid {segid} .or. "
        segid_vars = segid_vars + segid_add
    segid_tail = f") end"

    block = (
        f"!-------------------------------------------------------------------------------\n"
        f"! MOD: HBUILD control - preserve explicit H-coordinates\n"
        f"prnlev 5\n"
        f"echo START_HBUILD\n"
        f"{segid_head + segid_vars + segid_tail}\n"
        f"echo END_HBUILD\n"
        f"!-------------------------------------------------------------------------------\n"
    )
    return block


################################################################################
# PRINT USED PARAMETERS
################################################################################
def insert_parameter_print():
    block = (
        f"!-------------------------------------------------------------------------------\n"
        f"! MOD: Print used parameters\n"
        f"echo START_PAR\n"
        f"print para used\n"
        f"echo END_PAR\n"
        f"!-------------------------------------------------------------------------------\n"
    )
    return block


################################################################################
# OTHER FUNCTIONS
################################################################################


def streamWriter(work_dir, stream_name, blocks_as_lst):
    with open(f"{work_dir}/{stream_name}.str", "w") as ostr:
        for block in blocks_as_lst:
            ostr.write(block)


def inputFileInserter(inpfile, cases, blocks, inversions):
    assert len(cases) == len(blocks)

    # Check for the presence of a backup, and start from this
    # or make a backup if none exists
    if os.path.exists(f"{inpfile}.premod"):
        shutil.copy(f"{inpfile}.premod", f"{inpfile}")
    else:
        shutil.copy(f"{inpfile}", f"{inpfile}.premod")

    inp_backup = f"{inpfile}.premod"
    outfile = inpfile

    with open(outfile, "w") as out:
        with open(inp_backup, "r") as inf:
            for line in inf:
                for case, block, inversion in zip(cases, blocks, inversions):
                    if case in line:
                        if inversion == True:
                            line = f"{block}\n" f"\n" f"{case}\n"
                        elif inversion == None:
                            line = f"{block}\n"
                        else:
                            line = f"{case}\n" f"\n" f"{block}\n"
                out.write(line)


class Preparation:
    def __init__(self, parent_dir, ligand_id, original_dir):
        self.parent_dir = parent_dir
        self.ligand_id = ligand_id
        self.original_dir = original_dir

    def makeFolder(self, path):
        print(f"Being in the fuc=nciton {path}")
        try:
            os.makedirs(path)
            print(f"Creating folder in {path}")
        except OSError:
            print("but only here")
            if not os.path.isdir(path):
                raise

    def makeTFFolderStructure(self):
        self.makeFolder(f"{self.parent_dir}/{self.ligand_id}")
        self.makeFolder(f"{self.parent_dir}/{self.ligand_id}/complex")
        self.makeFolder(f"{self.parent_dir}/{self.ligand_id}/waterbox")

    def getTopparFromLocalCGenFF(
        ligands_dir, ligand_id, ligand_ext="mol2", cgenff_path=False, parent_dir="."
    ):
        cgenff_bin = None
        cgenff_output = None

        # If no particular path is given, check whether CGenFF is available
        if cgenff_path == False:
            cgenff_path = shutil.which("cgenff")
            if cgenff_path == None:
                print("This function requires cgenff.")
                print(
                    "Please install it in the active environment or point the routine"
                )
                print("to the right path using the key cgenff_path='/path/to/cgenff' .")
            else:
                cgenff_bin = cgenff_path
        else:
            cgenff_bin = cgenff_path

        # CGenFF exists - start program
        if cgenff_bin != None:

            # Run CGenFF
            ligand_path = f"{parent_dir}/{ligands_dir}/{ligand_id}.{ligand_ext}"

            cgenff_output = subprocess.run(  #
                [cgenff_bin]
                + [ligand_path]
                + ["-v"]
                + ["-f"]
                + [f"{ligand_id}/{ligand_id}.str"]
                + ["-m"]
                + [f"{ligand_id}/{ligand_id}.log"],  #
                # [cgenff_bin] + [ligand_path] + ["-v"] + ["-m"] + [f"{ligand_id}.log"],#
                capture_output=True,
                text=True,  #
            )

            # Evaluate the subprocess return code
            if cgenff_output.returncode == 1:
                print(f"CGenFF returned an error after being called with:\n")
                print(" ".join(cgenff_output.args))
                print(cgenff_output.stdout)
                print(cgenff_output.stderr)
            else:
                print(f"CGenFF executed successfully")
                # print(cgenff_output.stdout)
                # print(cgenff_output.stderr)

        return cgenff_output

    def createCRDfiles(self):

        pdb_file = pm.load_file(f"{self.original_dir}/{self.ligand_id}.pdb")
        df = pdb_file.to_dataframe()
        segids = set(i.residue.chain for i in pdb_file)
        print(f" die segids {segids}")
        if (
            len(segids) > 1
        ):  # for pdb file created with MAESTRO containing the chaing segment
            aa = [
                "ALA",
                "ARG",
                "ASN",
                "ASP",
                "CYS",
                "GLN",
                "GLU",
                "GLY",
                "HIS",
                "ILE",
                "LEU",
                "LYS",
                "MET",
                "PHE",
                "PRO",
                "SER",
                "THR",
                "TPO",
                "TRP",
                "TYR",
                "VAL",
                "HSD",
                "HSE",
            ]  # we need to finde the residue of the ligand which should be the only one beeing not an aa
            for chain in segids:  # renamin of the chain (a,b, ...) to segnames (proa,prob,...)
                for i in pdb_file.view[df.chain == f"{chain}"]:
                    if i.residue.name not in aa:
                        i.residue.chain = f"HETA"
                    else:
                        i.residue.chain = f"PRO{chain}"

            df = pdb_file.to_dataframe()
            segids = set(i.residue.chain for i in pdb_file)
            for segid in segids: # now we can save the crd files 
                if segid not in ["SOLV", "IONS"]:
                    if segid == "HETA":
                        pdb_file[df.chain == f"{segid}"].save(
                            f"{self.parent_dir}/{self.ligand_id}/complex/{segid.lower()}.crd",
                            overwrite=True,
                        )
                        pdb_file[df.chain == f"{segid}"].save(
                            f"{self.parent_dir}/{self.ligand_id}/waterbox/{segid.lower()}.crd",
                            overwrite=True,
                        )
                    else:
                        pdb_file[df.chain == f"{segid}"].save(
                            f"{self.parent_dir}/{self.ligand_id}/complex/{segid.lower()}.crd",
                            overwrite=True,
                        )

        else:  # CHARMM-GUI generated pdb files
            segids = set(i.residue.segid for i in pdb_file)
            for segid in segids:
                if segid not in ["SOLV", "IONS"]:
                    if segid == "HETA":
                        pdb_file[df.segid == f"{segid}"].save(
                            f"{self.parent_dir}/{self.ligand_id}/complex/{segid.lower()}.crd",
                            overwrite=True,
                        )
                        pdb_file[df.segid == f"HETA"].save(
                            f"{self.parent_dir}/{self.ligand_id}/waterbox/{segid.lower()}.crd",
                            overwrite=True,
                        )
                    else:
                        pdb_file[df.segid == f"{segid}"].save(
                            f"{self.parent_dir}/{self.ligand_id}/complex/{segid.lower()}.crd",
                            overwrite=True,
                        )
