import argparse
def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--country",
        type=str,
        default="India"
    )
    parser.add_argument("--category", default="finance",help="Category of news (finance, tech, health, politics, sports, lifestyle)"
    )

    return parser.parse_args()