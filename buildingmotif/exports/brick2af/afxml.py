import datetime
import os
from typing import Any, List, Tuple

# Prefer lxml for pretty printing; fall back to stdlib if unavailable
try:  # pragma: no cover - environment dependent
    from lxml import etree  # type: ignore
except Exception:  # pragma: no cover - fallback
    from xml.etree import ElementTree as etree  # type: ignore


class PIAFElement:
    element_type: str = ""
    element_attributes: List[str] = []
    element_enumerations: List[str] = []
    element_children: List[Tuple[str, type]] = []
    element_union: List[type] = []

    def __init__(self, *args, **kwargs):
        """Create an instance of a Asset Framework element."""
        self._children_by_name = dict(self.element_children)
        self._children_values = {}
        self._text = None

        if args:
            arg_value = args[0]
            if self.element_enumerations:
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if args[0] not in self.element_enumerations:
                    raise ValueError("invalid enumeration")
                self._text = args[0]

            elif self.element_union:
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                for subtype in self.element_union:
                    try:
                        value = subtype(args[0])
                        self._text = value._text
                        break
                    except (ValueError, TypeError):
                        pass
                else:
                    raise ValueError("invalid argument")

            elif self.element_type == "xs:boolean":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, bool):
                    raise TypeError("boolean expected")
                self._text = "true" if args[0] else "false"

            elif self.element_type == "xs:integer" or self.element_type == "xs:int":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, int):
                    raise TypeError("integer expected")
                self._text = f"{arg_value:d}"

            elif self.element_type == "xs:nonNegativeInteger":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, int):
                    raise TypeError("integer expected")
                if arg_value < 0:
                    raise ValueError("non-negative integer expected")
                self._text = f"{arg_value:d}"

            elif self.element_type == "xs:decimal":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, float):
                    raise TypeError("decimal (float) expected")
                self._text = f"{arg_value:f}"

            elif self.element_type == "xs:float":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, float):
                    raise TypeError("float expected")
                self._text = f"{arg_value:G}"

            elif self.element_type == "xs:string":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, str):
                    raise TypeError("string expected")
                self._text = arg_value

            elif self.element_type == "xs:date":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, datetime.date):
                    raise TypeError("datetime.date expected")
                self._text = arg_value.isoformat()

            elif self.element_type == "xs:time":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, datetime.time):
                    raise TypeError("datetime.time expected")
                self._text = arg_value.isoformat()

            elif self.element_type == "xs:dateTime":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, datetime.datetime):
                    raise TypeError("datetime.datetime expected")
                self._text = arg_value.isoformat()

            elif self.element_type == "xs:gMonthDay":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, datetime.date):
                    raise TypeError("datetime.date expected")
                self._text = arg_value.strftime("--%m-%d")

            elif self.element_type == "xs:gYear":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                if not isinstance(arg_value, int):
                    raise TypeError("integer expected")
                self._text = f"{arg_value:d}"

            elif self.element_type == "xs:any":
                if len(args) > 1:
                    raise RuntimeError("too many arguments")
                self._text = f"{arg_value}"

            else:
                # add the args as child elements
                for arg_value in args:
                    self += arg_value

        self._attributes = kwargs

    def __getattr__(self, attr):
        """Get the value of a child element."""
        if attr.startswith("_"):
            return object.__getattribute__(self, attr)

        # make sure the attribute exists and it has been given a value
        if attr not in self._children_by_name:
            raise AttributeError(
                f"{repr(self.__class__.__name__)} object has no child {repr(attr)}"
            )
        if attr not in self._children_values:
            raise ValueError(f"{repr(attr)} not set")

        # most of the time the elements are provided once, so returning the
        # one that was provided is easier, but if there is more than one
        # this returns the entire list
        values = self._children_values[attr]
        if len(values) == 1:
            return values[0]
        else:
            return values

    def __setattr__(self, attr, value):
        """Set the value of a child element."""
        if attr.startswith("_"):
            return super().__setattr__(attr, value)

        # make sure the attribute exists and the value is the correct type
        if attr not in self._children_by_name:
            raise AttributeError(
                f"{repr(self.__class__.__name__)} object has no child {repr(attr)}"
            )
        if not isinstance(value, self._children_by_name[attr]):
            raise ValueError(
                f"{repr(attr)} invalid type, expecting {self._children_by_name[attr]}"
            )

        # setting an attribute value is an error if there is already a value
        # that has been set
        if attr in self._children_values:
            raise ValueError(f"{repr(attr)} already set")

        # save the value
        self._children_values[attr] = [value]

    def __add__(self, value):
        """Add an element value by finding the child element name with the
        correct class.  Return this element so other child element values can
        be added like 'thing + Child1() + Child2()'.
        """
        for child_name, child_type in self.element_children:
            if isinstance(value, child_type):
                break
        else:
            child_type_names = list(
                child_type.__name__ for child_name, child_type in self.element_children
            )
            raise ValueError(f"expecting one of: {', '.join(child_type_names)}")

        # if this child already has a value, add this to the end
        if child_name in self._children_values:
            self._children_values[child_name].append(value)
        else:
            self._children_values[child_name] = [value]

        return self

    def __iadd__(self, value) -> None:
        """Statment form of 'add'."""
        return self + value

    def set(self, attr: str, value: str) -> None:
        """Set an XML attribute value for the element."""
        assert isinstance(value, str)
        self._attributes[attr] = value

    def __setitem__(self, item: str, value: str) -> None:
        """Array form 'element[attr] = value' of 'element.set(attr, value)."""
        assert isinstance(value, str)
        self._attributes[item] = value

    def get(self, attr: str) -> Any:
        """Return an XML attribute value for the element."""
        return self._attributes[attr]

    def __getitem__(self, item: str) -> str:
        """Array form of 'element.get(attr)'."""
        return self._attributes[item]

    def toxml(self, root=None, child_name=None) -> Any:
        """Return an ElementTree element.  If the root is provided the element
        will be a child of the root (a subelement).  If the child_name is
        provided it will be used for the element name, otherwise it defaults
        to the class name.
        """
        # if child name was provided, this element was part of a complex type
        # where the element name doesn't match the element type name
        element_name = child_name or self.__class__.__name__

        # if no root was provided, make one, otherwise this is a child
        # element of the root
        if root is None:
            attr_qname = etree.QName(
                "http://www.w3.org/2001/XMLSchema-instance", "noNamespaceSchemaLocation"
            )
            # pattern = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "**/OSIsoft.AF.xsd")
            # xsdpath = None
            # for fname in glob.glob(pattern, recursive=True):
            #     if os.path.isfile(fname):
            #         xsdpath = fname
            xsdpath = os.path.join(os.path.dirname(__file__), "OSIsoft.AF.xsd")
            if xsdpath is not None and isinstance(self, AF):
                myroot = etree.Element(
                    element_name,
                    {attr_qname: xsdpath},
                    nsmap={"xsi": "http://www.w3.org/2001/XMLSchema-instance"},
                )
            elif xsdpath is not None:
                myroot = etree.Element(element_name)
            else:
                print("error: XSD path not found")
        else:
            myroot = etree.SubElement(root, element_name)

        # maybe I have a value
        if self._text:
            myroot.text = str(self._text)

        # maybe I have attributes
        for k, v in self._attributes.items():
            myroot.set(k, v)

        # maybe I have children
        for child_name, child_type in self.element_children:
            for child_value in self._children_values.get(child_name, []):
                child_value.toxml(myroot, child_name)

        # return this "root" element
        return myroot

    def __str__(self):
        """Convert the element into a string."""
        return etree.tostring(self.toxml(), pretty_print=True).decode()


class id(PIAFElement):
    element_type = "xs:string"  # integer decimal bool string


class Name(PIAFElement):
    element_type = "xs:string"


class Description(PIAFElement):
    element_type = "xs:string"


class Template(PIAFElement):
    element_type = "xs:string"


class IsAnnotated(PIAFElement):
    element_type = "xs:boolean"


class DefaultAttribute(PIAFElement):
    element_type = "xs:string"


class DefaultInputPort(PIAFElement):
    element_type = "xs:string"


class DefaultOutputPort(PIAFElement):
    element_type = "xs:string"


class DefaultUndirectedPort(PIAFElement):
    element_type = "xs:string"


class Type(PIAFElement):
    element_type = "xs:string"


class FileName(PIAFElement):
    element_type = "xs:string"


class Author(PIAFElement):
    element_type = "xs:string"


class ChangeDate(PIAFElement):
    element_type = "xs:dateTime"


class Timestamp(PIAFElement):
    element_type = "xs:dateTime"


class FileSize(PIAFElement):
    element_type = "xs:long"


class Data(PIAFElement):
    element_type = "xs:string"


class Abbreviation(PIAFElement):
    element_type = "xs:string"


class RefFactor(PIAFElement):
    element_type = "xs:double"


class RefOffset(PIAFElement):
    element_type = "xs:double"


class RefFormulaFrom(PIAFElement):
    element_type = "xs:string"


class RefFormulaTo(PIAFElement):
    element_type = "xs:string"


class Factor(PIAFElement):
    element_type = "xs:double"


class Offset(PIAFElement):
    element_type = "xs:double"


class RefUOM(PIAFElement):
    element_type = "xs:string"


class AFClass(PIAFElement):
    element_type = "xs:string"


class AFAttributeCategoryRef(PIAFElement):
    element_type = "xs:string"


AFAttributeCategoryRef.element_children = [
    ("id", id),
]
AFAttributeCategoryRef.element_attributes = ["operation"]


class UOMGroup(PIAFElement):
    pass


UOMGroup.element_children = [("Name", Name), ("id", id), ("Description", Description)]


class UOMMapping(PIAFElement):
    element_type = "xs:string"


UOMMapping.element_children = [
    ("UOMGroup", UOMGroup),
    ("id", id),
]
UOMMapping.element_attributes = ["operation"]


class Status(PIAFElement):
    element_type = "xs:string"
    element_enumerations = ["NotReady", "Disabled", "Enabled", "Error"]


class IsHidden(PIAFElement):
    element_type = "xs:boolean"


class IsManualDataEntry(PIAFElement):
    element_type = "xs:boolean"


class IsConfigurationItem(PIAFElement):
    element_type = "xs:boolean"


class IsExcluded(PIAFElement):
    element_type = "xs:boolean"


class Trait(PIAFElement):
    element_type = "xs:string"


class DefaultUOM(PIAFElement):
    element_type = "xs:string"


class DisplayDigits(PIAFElement):
    element_type = "xs:string"


class TypeQualifier(PIAFElement):
    element_type = "xs:string"


TypeQualifier.element_attributes = ["type"]


class DataReference(PIAFElement):
    element_type = "xs:string"


DataReference.element_children = [("id", id)]


class ConfigString(PIAFElement):
    element_type = "xs:string"


class Item(PIAFElement):
    pass


class AFFile(PIAFElement):
    pass


AFFile.element_children = [
    ("FileName", FileName),
    ("Description", Description),
    ("Author", Author),
    ("ChangeDate", ChangeDate),
    ("FileSize", FileSize),
    ("Data", Data),
]


class UOM(PIAFElement):
    pass


UOM.element_children = [
    ("id", id),
    ("Name", Name),
    ("Abbreviation", Abbreviation),
    ("Description", Description),
    ("RefFactor", RefFactor),
    ("RefOffset", RefOffset),
    ("RefFormulaFrom", RefFormulaFrom),
    ("RefFormulaTo", RefFormulaTo),
    ("Factor", Factor),
    ("Offset", Offset),
    ("RefUOM", RefUOM),
    ("UOMMapping", UOMMapping),
    ("Class", AFClass),
]
UOM.element_attributes = ["operation"]


class Value(PIAFElement):
    element_type = "xs:any"


#     class Value(PIAFElement):


#     # class Value(PIAFElement):
#     #     element_type = 'xs:any'

# Value.element_children = [
#     ('Value', Value.Value),
#     ('AFFile', AFFile),
#     ('Item', Item),
# ]

Value.element_attributes = ["default", "type"]


class AFExtendedProperty(PIAFElement):
    pass


AFExtendedProperty.element_children = [
    ("id", id),
    ("Name", Name),
    ("Type", Type),
    ("Value", Value),
]


class AFValue(PIAFElement):
    pass


AFValue.element_children = [
    ("Status", Status),
    ("Timestamp", Timestamp),
    ("UOM", UOM),
    ("Value", Value),
]


class AFElementRef(PIAFElement):
    element_type = "xs:string"


class Target(PIAFElement):
    pass


Target.element_children = [("AFElementRef", AFElementRef)]


class AFPlugIn(PIAFElement):
    element_type = "xs:string"
    element_enumerations = []


class VariableMapping(PIAFElement):
    element_type = "xs:string"


class AFAnalysisRule(PIAFElement):
    pass


AFAnalysisRule.element_children = [
    ("AFPlugIn", AFPlugIn),
    ("ConfigString", ConfigString),
    ("VariableMapping", VariableMapping),
    ("AFAnalysisRule", AFAnalysisRule),
]


class AFTimeRule(PIAFElement):
    pass


AFTimeRule.element_children = [
    ("AFPlugIn", AFPlugIn),
    ("ConfigString", ConfigString),
    ("AFTimeRule", AFTimeRule),
]


class AFAnalysisCategoryRef(PIAFElement):
    element_type = "xs:string"


AFAnalysisCategoryRef.element_children = [("id", id)]


class AFAnalysis(PIAFElement):
    pass


AFAnalysis.element_children = [
    ("id", id),
    ("Name", Name),
    ("Description", Description),
    # ('Template', Template),
    # ('CaseTemplate', CaseTemplate),
    # ('OutputTime', OutputTime),
    ("Status", Status),
    # ('PublishResults', PublishResults),
    # ('Priority', Priority),
    # ('MaxQueueSize', MaxQueueSize),
    # ('GroupID', GroupID),
    ("Target", Target),
    ("AFExtendedProperty", AFExtendedProperty),
    ("AFAnalysisCategoryRef", AFAnalysisCategoryRef),
    ("AFAnalysisRule", AFAnalysisRule),
    ("AFTimeRule", AFTimeRule),
    # ('AFCase', AFCase),
    # ('SecurityAccessControl', SecurityAccessControl),
]


class AFAttribute(AFValue):
    pass


AFAttribute.element_children = [
    ("id", id),
    ("Name", Name),
    ("Description", Description),
    ("IsHidden", IsHidden),
    ("IsManualDataEntry", IsManualDataEntry),
    ("IsConfigurationItem", IsConfigurationItem),
    ("IsExcluded", IsExcluded),
    ("Trait", Trait),
    ("DefaultUOM", DefaultUOM),
    ("DisplayDigits", DisplayDigits),
    ("Type", Type),
    ("TypeQualifier", TypeQualifier),
    ("DataReference", DataReference),
    ("ConfigString", ConfigString),
    ("AFAttributeCategoryRef", AFAttributeCategoryRef),
    ("AFAttribute", AFAttribute),
]
AFAttribute.element_children.extend(AFValue.element_children)

AFAttribute.element_attributes = [
    "operation",
]


class AFBaseElement(PIAFElement):
    pass


AFBaseElement.element_children = [
    ("id", id),
    ("Name", Name),
    ("Description", Description),
    ("Template", Template),
    ("IsAnnotated", IsAnnotated),
    ("DefaultAttribute", DefaultAttribute),
    ("DefaultInputPort", DefaultInputPort),
    ("DefaultOutputPort", DefaultOutputPort),
    ("DefaultUndirectedPort", DefaultUndirectedPort),
]


class AFBaseElementChildren(PIAFElement):
    pass


AFBaseElementChildren.element_children = [
    ("AFExtendedProperty", AFExtendedProperty),
    #    ('AFElementCategoryRef', AFElementCategoryRef),
    ("AFAttribute", AFAttribute),
    # ('AFPort', AFPort),
    # ('AFAnnotation', AFAnnotation),
]


class AFElement(AFBaseElement, AFBaseElementChildren):
    pass


AFElement.element_children = []
AFElement.element_children.extend(AFBaseElement.element_children)
AFElement.element_children.extend(AFBaseElementChildren.element_children)
AFElement.element_children.extend(
    [
        ("AFElement", AFElement),
        # ('AFModel', AFModel),
        # ('AFElementRef', AFElementRef),
        # ('AFModelRef', AFModelRef),
        ("AFAnalysis", AFAnalysis),
        # ('AFNotificationRule', AFNotificationRule),
        # ('SecurityAccessControl', SecurityAccessControl),
    ]
)


AFElement.element_attributes = [
    "ReferenceType",
    "operation",
]


class AFAnalysisTemplate(PIAFElement):
    element_type = "xs:string"


AFAnalysisTemplate.element_children = [
    ("id", id),
    ("Name", Name),
    ("Description", Description),
    # ('OutputTime', OutputTime),
    # ('GroupID', GroupID),
    ##('CaseTemplate', CaseTemplate),
    ("Target", Target),
    # ('CreateEnabled', CreateEnabled),
    ("AFExtendedProperty", AFExtendedProperty),
    ("AFAnalysisCategoryRef", AFAnalysisCategoryRef),
    ("AFAnalysisRule", AFAnalysisRule),
    ("AFTimeRule", AFTimeRule),
    # ('SecurityAccessControl', SecurityAccessControl),
]

AFAnalysisTemplate.element_attributes = ["operation"]


class AFDatabase(PIAFElement):
    pass


AFDatabase.element_children = [
    ("AFExtendedProperty", AFExtendedProperty),
    ("id", id),
    ("Name", Name),
    # ('AFAnalysisCategory', AFAnalysisCategory),
    # ('AFAttributeCategory', AFAttributeCategory),
    # ('AFElementCategory', AFElementCategory),
    # ('AFReferenceTypeCategory', AFReferenceTypeCategory),
    # ('AFTableCategory', AFTableCategory),
    # ('AFTableConnection', AFTableConnection),
    # ('AFTable', AFTable),
    # ('AFEnumerationSet', AFEnumerationSet),
    # ('AFElementTemplate', AFElementTemplate),
    # ('AFNotificationTemplate', AFNotificationTemplate),
    # ('AFReferenceType', AFReferenceType),
    ("AFAnalysisTemplate", AFAnalysisTemplate),
    ("AFElement", AFElement),
    # ('AFModel', AFModel),
    # ('AFElementRef', AFElementRef),
    # ('AFEventFrame', AFEventFrame),
    # ('AFTransfer', AFTransfer),
    # ('AFAnalysis', AFAnalysis),
    # ('AFModelAnalysis', AFModelAnalysis),
    # ('AFNotification', AFNotification),
]
AFDatabase.element_attributes = [
    "operation",
]


class AF(PIAFElement):
    """Main AF element"""

    pass


AF.element_children = [
    ("AFDatabase", AFDatabase),
]
AF.element_attributes = [
    "id",
    "SoftwareVersion",
    "SchemaVersion",
    "ParentKey",
    "PISystem",
    "PIPersist",
    "Identity",
    "ExportedType",
    "ExportedObject",
    "ExportMode",
    "Description",
    "Database",
    "Created",
    "xmlns:xsi",
    "xsi:noNamespaceSchemaLocation",
]


class AFAttributeTemplate(PIAFElement):
    element_type = "xs:string"


AFAttributeTemplate.element_children = [
    ("id", id),
    ("Name", Name),
    ("Description", Description),
    ("IsHidden", IsHidden),
    ("IsManualDataEntry", IsManualDataEntry),
    ("IsConfigurationItem", IsConfigurationItem),
    ("IsExcluded", IsExcluded),
    # ('IsIndexed', IsIndexed),
    ("Trait", Trait),
    ("DefaultUOM", DefaultUOM),
    ("DisplayDigits", DisplayDigits),
    ("Type", Type),
    ("TypeQualifier", TypeQualifier),
    ("Value", Value),
    ("DataReference", DataReference),
    ("ConfigString", ConfigString),
    ("AFAttributeCategoryRef", AFAttributeCategoryRef),
    ("AFAttributeTemplate", AFAttributeTemplate),
]
AFAttributeTemplate.element_attributes = ["operation"]


class AFElementTemplate(PIAFElement):
    element_type = "xs:string"


AFElementTemplate.element_children = [
    ("id", id),
    ("Name", Name),
    ("Description", Description),
    ##('BaseTemplateOnly', BaseTemplateOnly),
    ##('BaseTemplate', BaseTemplate),
    ("Type", Type),
    # ('InstanceType', InstanceType),
    ##('AllowElementToExtend', AllowElementToExtend),
    ("DefaultAttribute", DefaultAttribute),
    ##('NamingPattern', NamingPattern),
    ("DefaultInputPort", DefaultInputPort),
    ("DefaultOutputPort", DefaultOutputPort),
    ("DefaultUndirectedPort", DefaultUndirectedPort),
    ##('Severity', Severity),
    ##('CanBeAcknowledged', CanBeAcknowledged),
    ("AFExtendedProperty", AFExtendedProperty),
    ##('AFElementCategoryRef', AFElementCategoryRef),
    ("AFAttributeTemplate", AFAttributeTemplate),
    ##('AFPort', AFPort),
    ("AFAnalysisTemplate", AFAnalysisTemplate),
    ##('AFNotificationRuleTemplate', AFNotificationRuleTemplate),
    # ('SecurityAccessControl', SecurityAccessControl),
]
AFElementTemplate.element_attributes = ["operation"]
