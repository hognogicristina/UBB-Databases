import cx_Oracle
import os
import re

cx_Oracle.init_oracle_client(lib_dir='/Users/cristinahognogi/instantclient_23_3')

username = 'hairbd0028'
password = 'hairbd002804'
dsn = '193.231.20.20:15211/orcl19c'

conn = cx_Oracle.connect(user=username, password=password, dsn=dsn)
executed_scripts = set()

script_order = [
    "1_create_tables_and_indexes.sql",
    "2_instructions_that_work.sql",
    "2_instructions_that_do_not_work.sql",
    "3_schema_check.sql",
    "4_procedure_get_mid_percent_books.sql",
    "5_view_available_procedures.sql",
    "6_get_procedure_source.sql",
    "1_clean_database.sql"
]


def clean_sql(sql_text):
    sql_no_multiline_comments = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)
    sql_no_single_line_comments = re.sub(r'--.*', '', sql_no_multiline_comments)
    return sql_no_single_line_comments


def get_script_index(script_name):
    return script_order.index(script_name) if script_name in script_order else -1


def script_exists(script_name):
    if get_script_index(script_name) == -1:
        print(f"Script {script_name} is not recognized.")
        return False

    script_path = os.path.join(os.getcwd(), script_name)
    if not os.path.exists(script_path):
        print(f"\nError: Script file '{script_path}' not found.")
        return False

    return True


def read_and_clean_script(script_name):
    script_path = os.path.join(os.getcwd(), script_name)

    with open(script_path, 'r') as file:
        raw_sql = file.read()

    return clean_sql(raw_sql)


def execute_procedure(cursor, procedure_sql):
    try:
        print("\nCreating procedure...")
        cursor.execute(procedure_sql)
        conn.commit()
        print("Procedure created successfully.")
        return True
    except Exception as error:
        print(f"Error creating procedure: {error}")
        conn.rollback()
        return False


def execute_statements(cursor, sql_block):
    statements = [stmt.strip() for stmt in sql_block.strip().split(';') if stmt.strip()]

    for statement in statements:
        execute_single_statement(cursor, statement)


def execute_single_statement(cursor, stmt):
    try:
        if stmt.lower().startswith("select"):
            cursor.execute(stmt)
            rows = cursor.fetchall()
            print(f"\nResult of SELECT:\n")
            for row in rows:
                print(row)
        else:
            cursor.execute(stmt)
    except Exception as stmt_err:
        print(f"Error executing statement:\n{stmt}\nError: {stmt_err}")


def print_dbms_output(cursor):
    statusVar = cursor.var(cx_Oracle.NUMBER)
    lineVar = cursor.var(cx_Oracle.STRING)

    while True:
        cursor.callproc("dbms_output.get_line", (lineVar, statusVar))
        if statusVar.getvalue() != 0:
            break
        print(lineVar.getvalue())


def handle_procedure_script(cursor, cleaned_sql):
    split_parts = cleaned_sql.split("END;")
    procedure_block = split_parts[0].strip() + "\nEND;"

    if not execute_procedure(cursor, procedure_block):
        return False

    remaining_sql = split_parts[1].strip() if len(split_parts) > 1 else ""
    if remaining_sql:
        execute_statements(cursor, remaining_sql)

    return True


def handle_procedure_books(cursor, cleaned_sql):
    pattern = re.compile(r'^(.*?END;)(.*)$', re.DOTALL | re.IGNORECASE)
    match = pattern.match(cleaned_sql)

    if not match:
        print("Could not split procedure and remaining SQL.")
        return False

    procedure_block = match.group(1).strip()
    remaining_sql = match.group(2).strip()

    if not execute_procedure(cursor, procedure_block):
        return False

    if remaining_sql:
        try:
            print(f"\nExecuting remaining block:\n{remaining_sql}\n{'-' * 40}")
            cursor.callproc("dbms_output.enable")
            cursor.execute(remaining_sql)
            print_dbms_output(cursor)
        except Exception as error:
            print(f"Error executing remaining SQL:\n{remaining_sql}\nError: {error}")
            return False

    return True


def execute_sql_script(script_name):
    if not script_exists(script_name):
        return

    print(f"\nExecuting {script_name} ...")
    cleaned_sql = read_and_clean_script(script_name)

    cursor = conn.cursor()

    try:
        if script_name == "4_procedure_get_mid_percent_books.sql":
            success = handle_procedure_books(cursor, cleaned_sql)
        elif script_name == "6_get_procedure_source.sql":
            success = handle_procedure_script(cursor, cleaned_sql)
        else:
            execute_statements(cursor, cleaned_sql)
            success = True

        if success:
            conn.commit()
            executed_scripts.add(script_name)
            print(f"Script {script_name} executed successfully!")
        else:
            print(f"Script {script_name} failed during execution.")

    except Exception as error:
        print(f"An error occurred while executing {script_name}: {error}")
        conn.rollback()

    finally:
        cursor.close()


if __name__ == "__main__":
    while True:
        print("\n===== ORACLE SQL SCRIPT EXECUTOR MENU =====")
        print("1. Run: Create tables and indexes")
        print("2. Run: Instructions (choose success/fail)")
        print("3. Run: Schema check")
        print("4. Run: Procedure -> Get Mid Percent Books")
        print("5. Run: View -> Available Procedures")
        print("6. Run: Procedure -> Get Procedure Source")
        print("7. Run: Clean database")
        print("0. Exit")

        try:
            cmd = int(input("Choose an option >> "))

            if cmd == 1:
                execute_sql_script("1_create_tables_and_indexes.sql")

            elif cmd == 2:
                print("\n== Instructions ==")
                print("1. Success (instructions that work)")
                print("2. Fail (instructions that do not work)")

                sub_cmd = int(input("Choose success (1) or fail (2) >> "))

                if sub_cmd == 1:
                    execute_sql_script("2_instructions_that_work.sql")
                elif sub_cmd == 2:
                    execute_sql_script("2_instructions_that_do_not_work.sql")
                else:
                    print("Invalid sub-option. Try again.")

            elif cmd == 3:
                execute_sql_script("3_schema_check.sql")
            elif cmd == 4:
                execute_sql_script("4_procedure_get_mid_percent_books.sql")
            elif cmd == 5:
                execute_sql_script("5_view_available_procedures.sql")
            elif cmd == 6:
                execute_sql_script("6_get_procedure_source.sql")
            elif cmd == 7:
                execute_sql_script("1_clean_database.sql")
            elif cmd == 0:
                print("Exiting...")
                break
            else:
                print("Invalid option. Try again.")
        except Exception as e:
            print(f"An error occurred: {e}")

    conn.close()
