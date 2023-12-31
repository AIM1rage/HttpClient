import asyncio
import contextlib
import os
import sys

from src.app.validator import validate_arguments
from src.app.completer_extensions import SingleWordCompleter
from socket import gaierror, herror
from ssl import SSLCertVerificationError
from asyncio.exceptions import TimeoutError
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import ProgressBar
from src.domain.http_client import (HttpClient,
                                    METHODS,
                                    BadRequestError,
                                    UnknownContentError,
                                    )
from src.app.client_argparser import ClientArgumentParser

completer = SingleWordCompleter(words=METHODS)


@contextlib.contextmanager
def none_context():
    yield None


def main_event(parser: ClientArgumentParser,
               client: HttpClient,
               session: PromptSession,
               ):
    try:
        if len(sys.argv) > 1:
            args = parser.parse_args(sys.argv[1:])
        else:
            args = parser.parse_args(
                session.prompt(HTML(
                    f'<MediumSeaGreen>http_client</MediumSeaGreen><yellow>@</yellow><tomato>{os.getlogin()}</tomato>> ')).split())
        headers = {name: value for name, value in args.header}
        validate_arguments(args)
    except (BadRequestError,
            FileNotFoundError,
            TypeError,
            ValueError,
            ) as e:

        print(e)
        return
    loop = asyncio.get_event_loop()
    with open(
            args.input,
            'rb',
    ) if args.input else none_context() as input_file, open(
        args.output,
        'wb',
    ) if args.output else none_context() as output_file:
        try:
            task = loop.create_task(
                client.request(args.method, args.url,
                               headers=headers,
                               file_content=input_file,
                               file_response=output_file,
                               verbose=args.verbose,
                               ))
            loop.run_until_complete(task)
            response = task.result()
            print('Failed...' if str(
                response.status_code).startswith(
                ('4', '5')) else 'Success!')
        except (BadRequestError,
                UnknownContentError,
                herror,
                gaierror,
                SSLCertVerificationError,
                OSError,
                TimeoutError,
                ) as e:
            task = loop.create_task(client.close())
            loop.run_until_complete(task)
            print('Failed...')
            print(e)


def main():
    parser = ClientArgumentParser(
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
    with ProgressBar() as progress_bar:
        client = HttpClient(progress_bar)
        session = PromptSession(completer=completer)
        while True:
            try:
                main_event(parser, client, session)
            except KeyboardInterrupt:
                ...
            except EOFError:
                print('Bye!')
                break
            if len(sys.argv) > 1:
                break


if __name__ == '__main__':
    main()
