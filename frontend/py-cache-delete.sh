#!/bin/bash

echo lösche Python-Cache in allen Unterverzeichnissen

find . -type d -name "__pycache__" -exec rm -r {} +

