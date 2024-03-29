"""
travers

(C) 2023 Justin Joyce.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


class MissingDependencyError(Exception):
    def __init__(self, dependency):
        self.dependency = dependency
        message = f"No module named '{dependency}' can be found, please install or include in requirements.txt"
        super().__init__(message)


class NodeNotFoundError(Exception):
    pass
