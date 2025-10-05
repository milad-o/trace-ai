"""Generate synthetic mainframe COBOL and JCL files for large-scale testing.

This script creates a realistic enterprise mainframe environment with:
- Multiple COBOL programs for different business functions
- JCL batch jobs that orchestrate COBOL program execution
- Complex data dependencies and workflows
- Scale: 50+ COBOL programs, 30+ JCL jobs, realistic file I/O

This simulates a real mainframe environment for proper scalability testing.
"""

from pathlib import Path
from typing import List, Dict
import random

OUTPUT_DIR = Path(__file__).parent / "sample_mainframe" / "synthetic"


# Business domains and their typical programs
BUSINESS_DOMAINS = {
    "CUSTOMER": [
        "CUST001 - Customer Master File Load",
        "CUST002 - Customer Address Validation",
        "CUST003 - Customer Credit Check",
        "CUST004 - Customer Account Update",
        "CUST005 - Customer Merge/Purge",
        "CUST006 - Customer Report Generator",
    ],
    "SALES": [
        "SALE001 - Daily Sales Extract",
        "SALE002 - Sales Transaction Validation",
        "SALE003 - Sales Commission Calculation",
        "SALE004 - Sales Summary Report",
        "SALE005 - Sales Forecast Generator",
        "SALE006 - Sales Tax Calculation",
    ],
    "INVENTORY": [
        "INV001 - Inventory Master Update",
        "INV002 - Inventory Reorder Point Check",
        "INV003 - Inventory Valuation Report",
        "INV004 - Inventory Movement Tracking",
        "INV005 - Inventory Reconciliation",
        "INV006 - Inventory Aging Analysis",
    ],
    "FINANCE": [
        "FIN001 - General Ledger Update",
        "FIN002 - Account Reconciliation",
        "FIN003 - Financial Statement Generator",
        "FIN004 - Budget vs Actual Report",
        "FIN005 - Cash Flow Analysis",
        "FIN006 - Tax Calculation Engine",
    ],
    "PAYROLL": [
        "PAY001 - Payroll Master File Load",
        "PAY002 - Payroll Hours Validation",
        "PAY003 - Payroll Tax Calculation",
        "PAY004 - Payroll Check Generation",
        "PAY005 - Payroll Deduction Processing",
        "PAY006 - Payroll Quarter-End Report",
    ],
    "BILLING": [
        "BILL001 - Invoice Generation",
        "BILL002 - Invoice Validation",
        "BILL003 - Payment Processing",
        "BILL004 - Aging Report",
        "BILL005 - Dunning Letter Generator",
        "BILL006 - Revenue Recognition",
    ],
}


def generate_cobol_program(
    program_id: str,
    program_name: str,
    input_files: List[str],
    output_files: List[str],
    called_programs: List[str] = None
) -> str:
    """Generate a synthetic COBOL program."""

    called_programs = called_programs or []

    # File control section
    file_control = []
    for i, input_file in enumerate(input_files, 1):
        file_control.append(f"""           SELECT {input_file.replace('.', '-')}-FILE
               ASSIGN TO {input_file}
               ORGANIZATION IS SEQUENTIAL.""")

    for i, output_file in enumerate(output_files, 1):
        file_control.append(f"""           SELECT {output_file.replace('.', '-')}-FILE
               ASSIGN TO {output_file}
               ORGANIZATION IS SEQUENTIAL.""")

    # FD sections
    fd_sections = []
    for input_file in input_files:
        fd_name = input_file.replace('.', '-')
        fd_sections.append(f"""       FD  {fd_name}-FILE.
       01  {fd_name}-RECORD.
           05  {fd_name}-KEY           PIC X(10).
           05  {fd_name}-DATA          PIC X(100).
           05  {fd_name}-AMOUNT        PIC 9(7)V99.
           05  {fd_name}-DATE          PIC X(10).
           05  FILLER                  PIC X(60).""")

    for output_file in output_files:
        fd_name = output_file.replace('.', '-')
        fd_sections.append(f"""       FD  {fd_name}-FILE.
       01  {fd_name}-RECORD.
           05  {fd_name}-KEY           PIC X(10).
           05  {fd_name}-DATA          PIC X(100).
           05  {fd_name}-AMOUNT        PIC 9(7)V99.
           05  {fd_name}-STATUS        PIC X(10).
           05  FILLER                  PIC X(60).""")

    # Procedure division paragraphs
    paragraphs = ["0000-MAIN", "1000-INITIALIZE", "2000-PROCESS-RECORDS", "3000-FINALIZE"]

    # PERFORM statements
    performs = "\n           ".join([f"PERFORM {p}" for p in paragraphs[1:]])

    # CALL statements
    calls = ""
    if called_programs:
        calls = "\n           " + "\n           ".join([
            f'CALL "{prog}" USING {input_files[0].replace(".", "-")}-RECORD'
            for prog in called_programs
        ])

    # Open/Close statements
    opens = "\n           ".join([
        f"OPEN INPUT {f.replace('.', '-')}-FILE" for f in input_files
    ] + [
        f"OPEN OUTPUT {f.replace('.', '-')}-FILE" for f in output_files
    ])

    closes = "\n           ".join([
        f"CLOSE {f.replace('.', '-')}-FILE" for f in input_files + output_files
    ])

    # Read/Write statements
    read_stmt = f"READ {input_files[0].replace('.', '-')}-FILE" if input_files else ""
    write_stmt = f"WRITE {output_files[0].replace('.', '-')}-RECORD" if output_files else ""

    cobol_code = f"""       IDENTIFICATION DIVISION.
       PROGRAM-ID. {program_id}.
      *****************************************************************
      * Program: {program_name}
      * Description: Processes {', '.join(input_files)} and produces
      *              {', '.join(output_files)}
      * Author: SYSTEM GENERATED
      * Date: 2024
      *****************************************************************

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
{chr(10).join(file_control)}

       DATA DIVISION.
       FILE SECTION.
{chr(10).join(fd_sections)}

       WORKING-STORAGE SECTION.
       01  WS-EOF-FLAG             PIC X VALUE 'N'.
           88  END-OF-FILE         VALUE 'Y'.
       01  WS-RECORD-COUNT         PIC 9(7) VALUE 0.
       01  WS-ERROR-COUNT          PIC 9(5) VALUE 0.
       01  WS-TOTAL-AMOUNT         PIC 9(9)V99 VALUE 0.

       PROCEDURE DIVISION.

       0000-MAIN.
           {performs}
           STOP RUN.

       1000-INITIALIZE.
           DISPLAY '*** {program_id} STARTED ***'
           {opens}
           MOVE 'N' TO WS-EOF-FLAG
           MOVE 0 TO WS-RECORD-COUNT
           MOVE 0 TO WS-ERROR-COUNT.

       2000-PROCESS-RECORDS.
           PERFORM UNTIL END-OF-FILE
               {read_stmt}
                   AT END
                       MOVE 'Y' TO WS-EOF-FLAG
                   NOT AT END
                       PERFORM 2100-VALIDATE-RECORD
                       PERFORM 2200-TRANSFORM-RECORD
                       {write_stmt}
                       ADD 1 TO WS-RECORD-COUNT
               END-READ
           END-PERFORM.{calls}

       2100-VALIDATE-RECORD.
           IF {input_files[0].replace('.', '-')}-KEY = SPACES
               ADD 1 TO WS-ERROR-COUNT
           END-IF.

       2200-TRANSFORM-RECORD.
           ADD {input_files[0].replace('.', '-')}-AMOUNT TO WS-TOTAL-AMOUNT.

       3000-FINALIZE.
           {closes}
           DISPLAY '*** {program_id} COMPLETED ***'
           DISPLAY 'RECORDS PROCESSED: ' WS-RECORD-COUNT
           DISPLAY 'ERRORS FOUND: ' WS-ERROR-COUNT
           DISPLAY 'TOTAL AMOUNT: ' WS-TOTAL-AMOUNT.
"""

    return cobol_code


def generate_jcl_job(
    job_name: str,
    steps: List[Dict[str, any]]
) -> str:
    """Generate a synthetic JCL job.

    Args:
        job_name: Name of the JCL job
        steps: List of steps, each with 'name', 'program', 'inputs', 'outputs'
    """

    jcl_steps = []

    for i, step in enumerate(steps, 1):
        step_name = step['name']
        program = step['program']
        inputs = step.get('inputs', [])
        outputs = step.get('outputs', [])

        # DD statements
        dd_statements = []

        for input_file in inputs:
            dd_name = input_file.replace('.', '').upper()[:8]
            dd_statements.append(f"//{dd_name:<8} DD DSN={input_file},DISP=SHR")

        for output_file in outputs:
            dd_name = output_file.replace('.', '').upper()[:8]
            dd_statements.append(f"//{dd_name:<8} DD DSN={output_file},DISP=(NEW,CATLG,DELETE),")
            dd_statements.append(f"//         SPACE=(TRK,(10,5),RLSE)")

        dd_statements.append(f"//SYSOUT   DD SYSOUT=*")

        step_code = f"""//STEP{i:03d}  EXEC PGM={program}
{chr(10).join(dd_statements)}"""

        jcl_steps.append(step_code)

    jcl_code = f"""//{{job_name}} JOB (ACCT),'BATCH JOB',
//             CLASS=A,
//             MSGCLASS=X,
//             MSGLEVEL=(1,1),
//             NOTIFY=&SYSUID
//*
//* Job: {job_name}
//* Description: Multi-step batch processing job
//* Generated: 2024
//*
{chr(10).join(jcl_steps)}
//"""

    return jcl_code


def create_synthetic_mainframe_environment():
    """Create a large synthetic mainframe environment."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cobol_dir = OUTPUT_DIR / "cobol"
    jcl_dir = OUTPUT_DIR / "jcl"
    cobol_dir.mkdir(exist_ok=True)
    jcl_dir.mkdir(exist_ok=True)

    print("\n🏭 Generating Synthetic Mainframe Environment...\n")

    all_programs = {}
    cobol_count = 0

    # Generate COBOL programs for each business domain
    for domain, programs in BUSINESS_DOMAINS.items():
        print(f"📦 Domain: {domain}")

        for prog_info in programs:
            prog_id, prog_name = prog_info.split(" - ")

            # Generate realistic file names
            input_files = [
                f"{domain}.INPUT.MASTER",
                f"{domain}.INPUT.TRANS",
            ]
            output_files = [
                f"{domain}.OUTPUT.{prog_id}",
                f"{domain}.REPORT.{prog_id}",
            ]

            # Some programs call utility programs
            called_programs = []
            if random.random() > 0.7:
                called_programs = [f"UTIL{random.randint(1,5):03d}"]

            # Generate COBOL program
            cobol_code = generate_cobol_program(
                prog_id, prog_name, input_files, output_files, called_programs
            )

            # Write to file
            cobol_file = cobol_dir / f"{prog_id}.cbl"
            cobol_file.write_text(cobol_code)

            all_programs[prog_id] = {
                'name': prog_name,
                'domain': domain,
                'inputs': input_files,
                'outputs': output_files,
                'called': called_programs
            }

            cobol_count += 1
            print(f"  ✓ Generated {prog_id}.cbl")

    print(f"\n✅ Generated {cobol_count} COBOL programs")

    # Generate JCL jobs that orchestrate workflows
    print(f"\n📋 Generating JCL Jobs...\n")

    jcl_count = 0

    # Daily batch jobs
    daily_jobs = {
        "DAILYCUS": ["CUST001", "CUST002", "CUST003"],
        "DAILYSAL": ["SALE001", "SALE002", "SALE003", "SALE004"],
        "DAILYINV": ["INV001", "INV002", "INV004"],
        "DAILYFIN": ["FIN001", "FIN002"],
        "DAILYPAY": ["PAY001", "PAY002", "PAY003"],
        "DAILYBIL": ["BILL001", "BILL002", "BILL003"],
    }

    for job_name, program_ids in daily_jobs.items():
        steps = []
        for i, prog_id in enumerate(program_ids, 1):
            if prog_id in all_programs:
                prog_info = all_programs[prog_id]
                steps.append({
                    'name': f"STEP{i:03d}",
                    'program': prog_id,
                    'inputs': prog_info['inputs'],
                    'outputs': prog_info['outputs']
                })

        jcl_code = generate_jcl_job(job_name, steps)
        jcl_file = jcl_dir / f"{job_name}.jcl"
        jcl_file.write_text(jcl_code)
        jcl_count += 1
        print(f"  ✓ Generated {job_name}.jcl ({len(steps)} steps)")

    # Weekly jobs
    weekly_jobs = {
        "WKLYINV": ["INV003", "INV005", "INV006"],
        "WKLYFIN": ["FIN003", "FIN004", "FIN005"],
        "WKLYSALE": ["SALE005", "SALE006"],
    }

    for job_name, program_ids in weekly_jobs.items():
        steps = []
        for i, prog_id in enumerate(program_ids, 1):
            if prog_id in all_programs:
                prog_info = all_programs[prog_id]
                steps.append({
                    'name': f"STEP{i:03d}",
                    'program': prog_id,
                    'inputs': prog_info['inputs'],
                    'outputs': prog_info['outputs']
                })

        jcl_code = generate_jcl_job(job_name, steps)
        jcl_file = jcl_dir / f"{job_name}.jcl"
        jcl_file.write_text(jcl_code)
        jcl_count += 1
        print(f"  ✓ Generated {job_name}.jcl ({len(steps)} steps)")

    # Monthly jobs
    monthly_jobs = {
        "MNTHPAY": ["PAY004", "PAY005", "PAY006"],
        "MNTHFIN": ["FIN006"],
        "MNTHBIL": ["BILL004", "BILL005", "BILL006"],
        "MNTHCUS": ["CUST004", "CUST005", "CUST006"],
    }

    for job_name, program_ids in monthly_jobs.items():
        steps = []
        for i, prog_id in enumerate(program_ids, 1):
            if prog_id in all_programs:
                prog_info = all_programs[prog_id]
                steps.append({
                    'name': f"STEP{i:03d}",
                    'program': prog_id,
                    'inputs': prog_info['inputs'],
                    'outputs': prog_info['outputs']
                })

        jcl_code = generate_jcl_job(job_name, steps)
        jcl_file = jcl_dir / f"{job_name}.jcl"
        jcl_file.write_text(jcl_code)
        jcl_count += 1
        print(f"  ✓ Generated {job_name}.jcl ({len(steps)} steps)")

    print(f"\n✅ Generated {jcl_count} JCL jobs")

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SYNTHETIC MAINFRAME ENVIRONMENT SUMMARY")
    print(f"{'='*60}")
    print(f"Location: {OUTPUT_DIR}")
    print(f"COBOL Programs: {cobol_count}")
    print(f"JCL Jobs: {jcl_count}")
    print(f"Business Domains: {len(BUSINESS_DOMAINS)}")
    print(f"\nExpected Graph Size:")
    print(f"  • Packages: ~{cobol_count + jcl_count}")
    print(f"  • Components (steps/paragraphs): ~{cobol_count * 4 + jcl_count * 3}")
    print(f"  • Data Sources: ~{cobol_count * 4}")
    print(f"  • Dependencies: ~{cobol_count * 5 + jcl_count * 3}")
    print(f"  • TOTAL NODES: ~{(cobol_count + jcl_count) + (cobol_count * 4 + jcl_count * 3) + (cobol_count * 4)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    create_synthetic_mainframe_environment()
