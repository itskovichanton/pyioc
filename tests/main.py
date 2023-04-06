from src.mybootstrap_ioc_itskovichanton.di import injector
from test_ioc import AbstractService


def main() -> None:
    x = injector().inject(AbstractService)
    x.do_smth()


if __name__ == '__main__':
    main()
