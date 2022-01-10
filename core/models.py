import json
from datetime import datetime
from operator import and_

from fastapi import Request
from sqlalchemy import Column, Integer, DateTime, text, or_, cast, String
from sqlalchemy.ext.declarative import declarative_base


class Model(object):
    __tablename__ = None

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_on = Column(DateTime, default=datetime.utcnow)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_table_name(cls):
        return cls.__tablename__


Model = declarative_base(cls=Model)


class QueryExecutor(object):

    def __init__(self, request: Request, query, mapper=None):
        self.request = request
        self.query = query
        self.mapper = mapper if mapper else self._get_cls_mapper()
        self.limit = self._process_limit()
        self.offset = self._process_offset()
        self.sort = self._process_sort()
        self.filters = self._process_filters()
        self._operators = {
            "contains": lambda c, v: c.ilike(f"%%{v}%%"),
            "eq": lambda c, v: c == v,
            "neq": lambda c, v: c != v,
            "gt": lambda c, v: c > v,
            "ge": lambda c, v: c >= v,
            "lt": lambda c, v: c < v,
            "le": lambda c, v: c <= v
        }
        self.filters_logic_map = {"or": or_, "and": and_}

        if self.filters:
            for obj in self.filters:
                logic = obj.get("logic")
                expressions = []

                for f in obj.get("filters"):
                    attr_name = f.get("field")
                    value = f.get("value")
                    operator = f.get("operator")

                    if not value:
                        continue

                    if operator not in self._operators:
                        raise KeyError(f"Expression `{attr_name}` has incorrect operator `{operator}`")

                    if not hasattr(self.mapper, attr_name):
                        raise KeyError(f"Expression `{attr_name}` does not exist in class mapper `{repr(self.mapper)}`")

                    column = cast(getattr(self.mapper, attr_name), String)
                    filter_query = self._operators[operator](column, value)
                    expressions.append(filter_query)

                if expressions and logic:
                    logic_func = self.filters_logic_map[logic]
                    self.query = self.query.filter(logic_func(*expressions))

        if self.sort:
            for sort in self.sort:
                direction = sort.get("dir")
                field = sort.get("field")

                if not direction or not field:
                    continue

                self.query = self.query.order_by(text(f"{field} {direction}"))

        if self.limit:
            self.query = self.query.limit(self.limit)

        if self.limit:
            self.query = self.query.offset(self.offset)

    def all(self):
        return self.query.all()

    def first(self):
        return self.query.first()

    def _process_limit(self):
        limit = self.request.query_params.get("limit")
        return int(limit) if limit else None

    def _process_offset(self):
        offset = self.request.query_params.get("offset")
        return int(offset) if offset else None

    def _process_sort(self):
        sort = self.request.query_params.get("sort")
        return json.loads(sort) if sort else None

    def _process_filters(self):
        filters = self.request.query_params.get("filters")
        return json.loads(filters) if filters else None

    def _get_cls_mapper(self):
        if not self.query.column_descriptions:
            return None

        return self.query.column_descriptions[0].get("entity")
