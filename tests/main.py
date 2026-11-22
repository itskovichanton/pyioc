from src.mybootstrap_ioc_itskovichanton import context

context.profile = "dev"

from src.mybootstrap_ioc_itskovichanton.di import injector
from test_ioc import AbstractService


def main() -> None:
    print(injector().inject(AbstractService).do_smth())


if __name__ == "__main__":
    main()
