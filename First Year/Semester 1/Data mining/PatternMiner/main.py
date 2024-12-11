from utils.analysis_options import analyze_data_with_options
from utils.data_loader import load_data

if __name__ == "__main__":
    while True:
        data = load_data()
        analyze_data_with_options(data)
