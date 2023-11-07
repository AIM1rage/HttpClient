import validators
import os
from src.domain.http_client import METHODS, BadRequestError


def validate_arguments(args):
    args.url = args.url if args.url.startswith(
        'http') else 'https://' + args.url
    if args.method.upper() not in METHODS:
        raise BadRequestError(f'Invalid method {args.method}')
    if not validators.url(args.url):
        raise ValueError(f'Invalid URL {args.url}')
    if args.input and not os.path.exists(args.input):
        raise FileNotFoundError(f'Input file doesn\'t exist')
