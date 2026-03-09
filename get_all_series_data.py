
from get_fed_series import fetch_and_save_fred_data
from get_m_square_chart import fetch_m_square_charts
from get_m_square_series import fetch_m_square_series
from get_ctfc_series import fetch_cftc_data


fetch_and_save_fred_data('STLFSI4')
fetch_m_square_charts()
fetch_m_square_series()
fetch_cftc_data()