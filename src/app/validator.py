import validators
import os
from src.domain.http_client import METHODS, BadRequestError


def validate_arguments(args):
    if args.method.upper() not in METHODS:
        raise BadRequestError(f'Invalid method {args.method}')
    if not validators.url(args.url):
        raise ValueError(f'Invalid URL {args.url}')
    if args.input:
        if not os.path.exists(args.input):
            raise FileNotFoundError(f'Input file doesn\'t exist')
        if not os.access(args.input, os.R_OK):
            raise PermissionError(f'Not enough rights to read')
    if args.output:
        if not os.access(args.output, os.W_OK):
            raise PermissionError(f'Not enough rights to read')
