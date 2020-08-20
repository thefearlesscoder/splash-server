from fastapi import APIRouter,  Security
from typing import List
from pydantic import parse_obj_as

from splash.models.compounds import Compound, NewCompound
from splash.models.users import UserModel
from splash.api import get_service_provider as services
from .auth import get_current_user

router = APIRouter()


@router.get("", tags=["compounds"], response_model=List[Compound])
def read_compounds(current_user: UserModel = Security(get_current_user)):
    compounds = services().compounds.retrieve_multiple(current_user, 1)
    results = parse_obj_as(List[Compound], compounds)
    return results


@router.get("/{uid}", tags=['compounds'])
def read_compound(
        uid: str,
        current_user: UserModel = Security(get_current_user)):

    compound_dict = services().compounds.retrieve_one(current_user, uid)
    return (Compound(**compound_dict))


@router.post("", tags=['compounds'])
def create_compound(
        new_compound: NewCompound,
        current_user: UserModel = Security(get_current_user)):
    uid = services().compounds.create(new_compound)
    return uid
