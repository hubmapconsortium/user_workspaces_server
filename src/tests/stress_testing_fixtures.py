import json


def get_workspace_data(globus_token: str, with_linked_datasets: bool, uuids: list[int]):
    if with_linked_datasets:
        uuid_list = []
        symlinks = []
        if len(uuids) == 0:
            raise Exception("List of UUIDs required to link datasets to new workspace.")
        for uuid in uuids:
            uuid_list.append(str(uuid))
            symlinks.append({"dataset_uuid": str(uuid), "name": f"datasets/{uuid}"})
            return {
                "globus_groups_token": globus_token,
                "files": [
                    {
                        "name": "blank.ipynb",
                        "content": json.dumps(
                            {
                                "cells": [
                                    {
                                        "cell_type": "code",
                                        "execution_count": None,
                                        "metadata": {},
                                        "outputs": [],
                                        "source": [
                                            "# linked datasets",
                                            f"uuids = {uuids}",
                                        ],
                                    }
                                ],
                                "metadata": {},
                                "nbformat": 4,
                                "nbformat_minor": 5,
                            },
                        ),
                    }
                ],
                "symlinks": symlinks,
            }
    else:
        return {
            "files": [
                {
                    "name": "jupyter_notebooks/blank.ipynb",
                    "content": '{\n "cells": [\n  {\n   "cell_type": "markdown",\n   "id": "e399c39d",\n   "metadata": {},\n   "source": [\n    "Test workspace!"\n   ]}]}',
                }
            ]
        }
