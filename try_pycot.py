from pycot.reports import CommitmentsOfTraders

cot = CommitmentsOfTraders("legacy_fut")
contract_names = ("FED FUNDS - CHICAGO BOARD OF TRADE", "30-DAY FEDERAL FUNDS - CHICAGO BOARD OF TRADE")
df = cot.report(contract_names)
df
