import asyncio
import argparse
import contextlib
import os

from validator import validate_arguments
from completer_extensions import SingleWordCompleter
from socket import gaierror, herror
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import ProgressBar
from prompt_toolkit.formatted_text import HTML

from src.http_client import HttpClient, BadRequestError, METHODS

completer = SingleWordCompleter(words=METHODS)


@contextlib.contextmanager
def some_context():
    yield None


def main():
    parser = argparse.ArgumentParser(
        prog='HTTP client',
        description='Program for sending HTTP requests and receiving responses from servers to interact with web services and retrieve data',
    )
    parser.add_argument('method', type=str,
                        help='Describes one of the available HTTP request methods')
    parser.add_argument('url', type=str,
                        help='A string that identifies the location of a resource on the internet')
    parser.add_argument('-H', '--header',
                        default=[],
                        nargs='*',
                        metavar=('key', 'value'),
                        action='append',
                        help='A key-value pair that provides additional information related to an HTTP request')
    parser.add_argument('-i', '--input', type=str,
                        default=None,
                        help='The path of the HTTP request content.')
    parser.add_argument('-o', '--output', type=str,
                        default=None,
                        help='The file path where the HTTP response will be saved.')
    parser.add_argument('-t', '--timeout', type=float,
                        default=5,
                        help='The timeout for the HTTP response')
    parser.add_argument('-v', '--verbose', type=int,
                        default=1,
                        help='Informative and detailed response. Set verbose value to 0 to get less information')
    client = HttpClient()
    session = PromptSession(completer=completer)
    while True:
        try:
            args = parser.parse_args(
                session.prompt(HTML(
                    f'<MediumSeaGreen>http_client</MediumSeaGreen><yellow>@</yellow><tomato>{os.getlogin()}</tomato>> ')).split())
            headers = {name: value for name, value in args.header}

            try:
                validate_arguments(args)
            except (BadRequestError,
                    FileNotFoundError,
                    PermissionError,
                    TypeError,
                    ValueError,
                    ) as e:
                print(e)
                continue

            with open(
                    args.input,
                    'rb',
            ) if args.input else some_context() as input_file, open(
                args.output,
                'wb',
            ) if args.output else some_context() as output_file:
                try:
                    loop = asyncio.get_event_loop()
                    task = loop.create_task(
                        client.request(args.method, args.url,
                                       headers=headers,
                                       file_content=input_file,
                                       file_response=output_file,
                                       verbose=args.verbose,
                                       ))
                    loop.run_until_complete(task)
                    response = task.result()
                except (BadRequestError,
                        herror,
                        gaierror,
                        ) as e:
                    print(e)
        except KeyboardInterrupt:
            ...
        except EOFError:
            print('Bye!')
            break


if __name__ == '__main__':
    main()
