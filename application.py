import asyncio
import argparse
import os.path

import validators

from validators import ValidationError

from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import ProgressBar
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import WordCompleter

from src.http_client import HttpClient, BadRequestError, METHODS

completer = WordCompleter(METHODS)


def validate_arguments(args):
    if args.method.upper() not in METHODS:
        raise BadRequestError(f'Invalid method {args.method}')
    if not validators.url(args.url):
        raise ValidationError(f'Invalid URL {args.url}')
    if args.input:
        if not os.path.exists(args.input):
            raise FileNotFoundError(f'Input file doesn\'t exist')
        if not os.access(args.input, os.R_OK):
            raise PermissionError(f'Not enough rights to read')
    if args.output:
        if not os.access(args.output, os.W_OK):
            raise PermissionError(f'Not enough rights to read')


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
    client = HttpClient()
    while True:
        try:
            args = parser.parse_args(
                prompt(HTML(
                    '<MediumSeaGreen>Http Client</MediumSeaGreen>> ')).split())

            try:
                validate_arguments(args)
            except (BadRequestError,
                    ValidationError,
                    FileNotFoundError,
                    PermissionError,
                    ) as e:
                print(e)

            headers = {name: value for name, value in args.header}

            with open(args.input, 'rb') as input_file, open(
                    args.output, 'wb') as output_file:
                try:
                    loop = asyncio.get_event_loop()
                    task = loop.create_task(
                        client.request(args.method, args.url,
                                       headers=headers,
                                       file_content=input_file,
                                       file_response=output_file,
                                       ))
                    loop.run_until_complete(task)
                    response = task.result()
                except BadRequestError as e:
                    print(e)
        except KeyboardInterrupt:
            ...
        except EOFError:
            print('Bye!')
            break


if __name__ == '__main__':
    main()
