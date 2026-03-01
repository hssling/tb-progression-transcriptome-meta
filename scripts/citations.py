from tbmeta.config import ensure_dirs, load_config
from tbmeta.reporting.citations import generate_bibliography


def main() -> None:
    cfg = load_config("configs/config.yaml")
    ensure_dirs(cfg)
    out = generate_bibliography(cfg)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
