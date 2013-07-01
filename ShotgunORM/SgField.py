# Copyright (c) 2013, Nathan Dunsworth - NFXPlugins
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the NFXPlugins nor the names of its contributors
#       may be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL NFXPLUGINS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

__all__ = [
  'SgField',
  'SgFieldInfo',
  'SgUserField'
]

# Python imports
import copy
import string
import threading
import weakref

from xml.etree import ElementTree as ET

# This module imports
import ShotgunORM

# Set later in this file.
FIELD_RETURN_TYPES = {}

class SgFieldQueryProfiler(object):
  '''
  Field profiler.
  '''

  def __init__(self):
    self._fieldProfiles = {}

  def profile(self, sgField):
    if not ShotgunORM.config.ENABLE_FIELD_QUERY_PROFILING:
      return

    entity = sgField.parentEntity()

    if entity == None:
      return

    entityType = entity.type
    url = entity.connection().url().lower()

    field = sgField.name()

    if not self._fieldProfiles.has_key(url):
      data = {
        entityType: {
          field: 1
        }
      }

      self._fieldProfiles[url] = data
    elif not self._fieldProfiles[url].has_key(entityType):
      self._fieldProfiles[url][entityType] = {
        field: 1
      }
    elif not self._fieldProfiles[url][entityType].has_key(field):
      self._fieldProfiles[url][entityType][field] = 1
    else:
      self._fieldProfiles[url][entityType][field] += 1

  def reset(self):
    self._fieldProfiles = {}

class SgFieldInfo(object):
  '''
  Class that represents a Shotgun Entities field information.
  '''

  def __repr__(self):
    return '<%s.%s name:%s, label:%s, valueTypes:%s>' % (
      self.__module__,
      self.__class__.__name__,
      self.name(),
      self.label(),
      self.valueTypes()
    )

  def __init__(self, sgFieldAttribs):
    self._initialized = False

    self._defaultValue = sgFieldAttribs['default_value']
    self._doc = sgFieldAttribs['doc']
    self._editable = sgFieldAttribs['editable']
    self._label = sgFieldAttribs['label']
    self._name = sgFieldAttribs['name']
    self._parent = sgFieldAttribs['parent']
    self._required = sgFieldAttribs['required']
    self._returnType = sgFieldAttribs['return_type']
    self._returnTypeName = sgFieldAttribs['return_type_name']
    self._summaryInfo = sgFieldAttribs['summary_info']
    self._valueTypes = sgFieldAttribs['value_types']
    self._validValues = sgFieldAttribs['valid_values']

  @classmethod
  def fromSg(self, sgEntityName, sgEntityLabel, sgFieldName, sgSchema):
    '''
    Returns a new SgFieldInfo that is constructed from the arg "sgSchema".
    '''

    data = {
      'default_value': sgSchema['properties']['default_value']['value'],
      'doc': '',
      'editable': sgSchema['editable']['value'],
      'label': sgSchema['name']['value'],
      'name': sgFieldName,
      'parent': sgSchema['entity_type']['value'],
      'required': sgSchema['mandatory']['value'],
      'return_type': FIELD_RETURN_TYPES.get(
        sgSchema['data_type']['value'],
        SgField.RETURN_TYPE_UNSUPPORTED
      ),
      'return_type_name': sgSchema['data_type']['value'],
      'summary_info': None,
      'value_types': None,
      'valid_values': []
    }

    try:
      data['value_types'] = copy.deepcopy(
        sgSchema['properties']['valid_types']['value']
      )
    except:
      pass

    try:
      data['valid_values'] = copy.deepcopy(
        sgSchema['properties']['valid_values']['value']
      )
    except:
      pass

    if data['return_type_name'] == 'summary':
      props = sgSchema['properties']

      expData = {
        'entity_type': props['query']['value']['entity_type'],
        'filters': props['query']['value']['filters'],
        'summary_type': props['summary_default']['value'],
        'summary_field': props['summary_field']['value'],
        'summary_value': props['summary_value']['value']
      }

      data['summary_info'] = copy.deepcopy(expData)

    return self(data)

  @classmethod
  def fromXML(self, sgEntityName, sgEntityLabel, sgXmlElement):
    '''
    Returns a new SgFieldInfo that is constructed from the arg "sgXmlElement".
    '''

    if sgXmlElement.tag != 'SgField':
      raise RuntimeError('invalid tag "%s"' % sgXmlElement.tag)

    data = {
      'default_value': sgXmlElement.attrib.get('default_value'),
      'doc': sgXmlElement.attrib.get('doc'),
      'editable': sgXmlElement.attrib.get('editable') == 'True',
      'label': sgXmlElement.attrib.get('label'),
      'name': sgXmlElement.attrib.get('name'),
      'parent': sgXmlElement.attrib.get('parent'),
      'required': bool(sgXmlElement.attrib.get('required')),
      'return_type': int(sgXmlElement.attrib.get('return_type')),
      'return_type_name': sgXmlElement.attrib.get('return_type_name'),
      'summary_info': eval(sgXmlElement.attrib.get('summary_info')),
      'value_types': sgXmlElement.attrib.get('value_types'),
      'valid_values': sgXmlElement.attrib.get('valid_values'),
    }

    if data['value_types'] == '':
      data['value_types'] = []
    else:
      data['value_types'] = data['value_types'].split(',')

    if data['valid_values'] == '':
      data['valid_values'] = []
    else:
      data['valid_values'] = data['valid_values'].split(',')

    return self(data)

  def defaultValue(self):
    '''
    Returns the default value of the field.
    '''

    return self._defaultValue

  def doc(self):
    '''
    Returns the fields doc string.
    '''

    return self._doc

  def isEditable(self):
    '''
    Returns True if the field is editable.
    '''

    return self._editable

  def isRequired(self):
    '''
    Returns True if the field is required for the Entity.
    '''

    return self._required

  def name(self):
    '''
    Returns the name of the field used by Shotguns api.  This is NOT the user
    friendly name displayed in a web-browser.
    '''

    return self._name

  def label(self):
    '''
    Returns the name of the field visible to users.  This is the user friendly
    name displayed in a web-browser.
    '''

    return self._label

  def parentEntity(self):
    '''
    Returns the name of the parent Entity to which the field belongs to.
    '''

    return self._parent

  def returnType(self):
    '''
    Returns the SgField.RETURN_TYPE value of the field.
    '''

    return self._returnType

  def returnTypeName(self):
    '''
    Returns string that is the return type value from Shotgun.
    '''
    return self._returnTypeName

  def summaryInfo(self):
    '''
    For summary field infos this returns the data to build the search expression.
    '''

    return copy.deepcopy(self._summaryInfo)

  def toXML(self):
    '''
    Returns a ElementTree Element that represents the field info.

    See also:
    SgSchema.export(...)
    '''

    doc = self.doc()
    editable = str(self.isEditable())
    label = self.label()
    name = self.name()
    parent = self.parentEntity()
    required = str(self.isRequired())
    return_type = str(self.returnType())
    return_type_name = self.returnTypeName()
    summary_info = str(self.summaryInfo())
    value_types = self.valueTypes()
    valid_values = self.validValues()

    if value_types == None:
      value_types = ''
    else:
      value_types = string.join(value_types, ',')

    if valid_values == None:
      valid_values = ''
    else:
      valid_values = string.join(valid_values, ',')

    result = ET.Element(
      'SgField',
      doc=doc,
      editable=editable,
      label=label,
      name=name,
      parent=parent,
      required=required,
      return_type=return_type,
      return_type_name=return_type_name,
      summary_info=summary_info,
      value_types=value_types,
      valid_values=valid_values
    )

    return result

  def validValues(self):
    '''
    Returns a list of valid values supported by the field.

    Returns an empty list when the field in Shotgun does not require certain
    values.
    '''

    result = []

    for i in self._validValues:
      result.append(i)

    return result

  def valueTypes(self):
    '''
    Returns the supported value types of the SgField.

    Returns None when the field in Shotgun does require certain value types.
    '''

    return self._valueTypes

class SgField(object):
  '''
  A Class that represents a Shotgun Entity field.
  '''

  RETURN_TYPE_UNSUPPORTED = -1
  RETURN_TYPE_CHECKBOX = 0
  RETURN_TYPE_COLOR = 1
  RETURN_TYPE_COLOR2 = 2
  RETURN_TYPE_DATE = 3
  RETURN_TYPE_DATE_TIME = 4
  RETURN_TYPE_ENTITY = 5
  RETURN_TYPE_FLOAT = 6
  RETURN_TYPE_IMAGE = 7
  RETURN_TYPE_INT = 8
  RETURN_TYPE_LIST = 9
  RETURN_TYPE_MULTI_ENTITY = 10
  RETURN_TYPE_SERIALIZABLE = 11
  RETURN_TYPE_STATUS_LIST = 12
  RETURN_TYPE_SUMMARY = 13
  RETURN_TYPE_TAG_LIST = 14
  RETURN_TYPE_TEXT = 15
  RETURN_TYPE_URL = 16

  # Custom return types should start at 201.
  RETURN_TYPE_RESERVED = 200

  __fieldclasses__ = {
    'default': {
      RETURN_TYPE_UNSUPPORTED: None
    },
    'entities': {}
  }

  __profiler__ = SgFieldQueryProfiler()

  def __repr__(self):
    return '<%s>' % ShotgunORM.mkEntityFieldString(self)

  def __enter__(self):
    # Grab the parent immediately and dont use self.hasParentEntity() because
    # field parents are weakref'd and you might lose the Entity.
    parent = self.parentEntity()

    # Lock the parent if the field has one.
    if parent != None:
      parent._SgEntity__lock.acquire()

  def __exit__(self, exc_type, exc_value, traceback):
    # Grab the parent immediately and dont use self.hasParentEntity() because
    # field parents are weakref'd and you might lose the Entity.
    parent = self.parentEntity()

    # Lock the parent if the field has one.
    if parent != None:
      parent._SgEntity__lock.release()

    return False

  def __init__(self, parentEntity, fieldInfo):
    self._parent = weakref.ref(parentEntity)
    self._info = fieldInfo
    self._widget = None

    self._value = fieldInfo.defaultValue()
    self._updateValue = None

    self.__hasCommit = False
    self.__hasSyncUpdate = False
    self.__valid = False

    self.__isCommitting = False
    self.__isUpdatingEvent = threading.Event(verbose=True)

    self.__isUpdatingEvent.set()

  @classmethod
  def registerFieldClass(cls, sgFieldReturnType, sgFieldClass):
    '''
    Registers a field class.

    Args:
      * (int) sgFieldReturnType:
        SgField.RETURN_TYPE

      * (class) sgFieldClass:
        Class to use for the field return type.
    '''

    cls.__fieldclasses__[sgFieldReturnType] = sgFieldClass

  def canSync(self):
    '''
    Returns True if the field is in a state that can be updated by a sync call.

    Fields that return False for isQueryable() will always cause this to return
    False.
    '''

    parent = self.parentEntity()

    if not self.isQueryable() or parent == None or not parent.exists():
      return False

    return not (self.isValid() or self.hasSyncUpdate() or self.isSyncUpdating())

  def changed(self):
    '''
    Called whenever the fields value changes.

    This calls updateWidget() and if the field has a parent Entity it calls
    the Entities onFieldChanged() with self.
    '''

    self.updateWidget()

    parent = self.parentEntity()

    if parent == None:
      return

    parent.onFieldChanged(self)

  def defaultValue(self):
    '''
    Returns the default value for the field.
    '''

    return self.info().defaultValue()

  def _deleteWidget(self):
    '''
    Sub-class portion of SgField.deleteWidget().

    Note:
      This is only called by deleteWidget() if widget() is not None.
    '''

    pass

  def deleteWidget(self):
    '''
    Deletes the widget of the field.

    Returns True if the widget existed and was in fact deleted.
    '''

    with self:
      if self.widget() != None:
        self._deleteWidget()

        return True

      return False

  def doc(self):
    '''
    Returns the fields doc string.
    '''

    return self.info().doc()

  def eventLogs(self, sgEventType=None, sgRecordLimit=0):
    '''
    Returns the event log Entities for the field.

    When the field has no parent or the parent Entity does not yet exist in
    Shotgun an empty list is returned.

    Args:
      * (str) sgEventType:
        Event type filter such as "Shotgun_Asset_Change".

      * (int) sgRecordLimit:
        Limits the amount of returned events.
    '''

    parent = self.parentEntity()

    # If the parent is none or if the parent does not exist, meaning you can't
    # do any queries for event info, bail.
    if parent == None or not parent.exists():
      return []

    connection = parent.connection()

    filters = [
      [
        'entity',
        'is',
        parent
      ],
      [
        'attribute_name',
        'is',
        self.name()
      ]
    ]

    order = [
      {
        'field_name': 'created_at',
        'direction': 'desc'
      }
    ]

    if sgEventType != None:
      filters.append(
        [
          'event_type',
          'is',
          sgEventType
        ]
      )

    result = connection.find(
      'EventLogEntry',
      filters,
      order=order,
      limit=sgRecordLimit
    )

    return result

  def _fromFieldData(self, sgData):
    '''
    Sub-class portion of SgField.fromFieldData().

    Note:
      Sub-classes only need to convert the incoming data to their internal
      format and return True.

      You should check if the incoming value is the same as the current value
      and in those cases do nothing and return False.

      valid() and hasCommit() are set based upon the return result of True/False.

    Args:
      * (dict) sgData:
        Dict of Shotgun formatted Entity field values.
    '''

    return False

  def fromFieldData(self, sgData):
    '''
    Sets the fields value from data returned by a Shotgun query.

    Returns True on success.

    Args:
      * (dict) sgData:
        Dict of Shotgun formatted Entity field values.
    '''

    with self:
      ShotgunORM.LoggerField.debug('%(sgField)s.fromFieldData()', {'sgField': self})
      ShotgunORM.LoggerField.debug('    * sgData: %(sgData)s', {'sgData': sgData})

      parent = self.parentEntity()

      if not self.isEditable():
        raise RuntimeError('%s is not editable!' % ShotgunORM.mkEntityFieldString(self))

      self.validate()

      result = self._fromFieldData(sgData)

      if not result:
        return False

      self.setValid(True)
      self.setHasCommit(True)

      self.changed()

      return True

  def hasCommit(self):
    '''
    Returns True if the fields value has changed but it has not been published
    to the Shotgun database.
    '''

    return self.__hasCommit

  def hasParentEntity(self):
    '''
    Returns True if the field has a parent Entity.

    Note:
      Because fields weakref their parent you should not use this as a test if
      its safe to call SgField.parentEntity() as it might have been gc'd
      inbetween the two calls.
    '''

    return self.parentEntity() != None

  def hasSyncUpdate(self):
    '''
    Returns True if the fields value was retrieved from Shotgun and is awaiting
    validate to set value to it.
    '''

    return self.__hasSyncUpdate

  def info(self):
    '''
    Returns the SgFieldInfo object that describes the field.
    '''

    return self._info

  def _invalidate(self):
    '''
    Sub-class portion of SgField.invalidate().
    '''

    pass

  def invalidate(self):
    '''
    Invalidates the stored value of the field so that the next call to value()
    will force a re-evaluate its value.
    '''

    with self:
      ShotgunORM.LoggerField.debug('%(sgField)s.invalidate()', {'sgField': self})

      self.__isUpdatingEvent.wait()

      self.setHasCommit(False)
      self.setHasSyncUpdate(False)
      self.setValid(False)

      self._value = self.defaultValue()
      self._updateValue = None

      self._invalidate()

  def isCacheable(self):
    '''
    Returns True if the field is cacheable.

    Default returns the value of...

    hasCommit() and (isValid() or hasSyncUpdate())

    This is queried when a an Entities __del__ is called.  If True then the
    Entity will cache the fields value on the SgConnection.
    '''

    return not self.hasCommit() and (self.isValid() or self.hasSyncUpdate())

  def isCommitting(self):
    '''
    Returns True if the field is currently being commited to Shotgun.

    When this is True the field is locked and unable to change its value.
    '''

    return self._isCommitting

  def isCommittable(self):
    '''
    Returns True if the field is allowed to make commits to Shotgun.

    Default returns self.isQueryable()
    '''

    return self.isQueryable()

  def isCustom(self):
    '''
    Returns True if the fields API name starts with "sg_".
    '''

    return self.name().startswith('sg_')

  def isEditable(self):
    '''
    Returns True if the field is editable in Shotgun.

    When the parent Entity does not exist in Shotgun non-editable fields are
    modifyable.
    '''

    parent = self.parentEntity()

    if parent == None:
      return self.info().isEditable()
    else:
      return self.info().isEditable() or not parent.exists()

  def isQueryable(self):
    '''
    Returns True if the field is queryable in Shotgun.

    Default returns True.
    '''

    return True

  def isSyncUpdating(self):
    '''
    Returns True if the field is retrieving its value from Shotgun.

    When this is True the field is locked and unable to change its value.
    '''

    return not self.__isUpdatingEvent.isSet()

  def isValid(self):
    '''
    Returns True if the field is valid.

    This returns False when the field hasn't yet performed a query to Shotgun
    for its value or invalidate has been called.
    '''

    return self.__valid

  def label(self):
    '''
    Returns the user visible string of the field.
    '''

    return self.info().label()

  def lastEventLog(self, sgEventType=None):
    '''
    Returns the last event log Entity for this field.

    If no event log exists or the Entity contains no parent or the parent does
    not yet exist in Shotgun None is returned.

    Args:
      * (str) sgEventType:
        Event type filter such as "Shotgun_Asset_Change".
    '''

    parent = self.parentEntity()

    if parent == None or not parent.exists():
      return None

    connection = parent.connection()

    filters = [
      [
        'entity',
        'is',
        parent
      ],
      [
        'attribute_name',
        'is',
        self.name()
      ]
    ]

    order = [
      {
        'field_name': 'created_at',
        'direction': 'desc'
      }
    ]

    if sgEventType != None:
      filters.append(
        [
          'event_type',
          'is',
          sgEventType
        ]
      )

    result = connection.findOne(
      'EventLogEntry',
      filters,
      order=order
    )

    return result

  def _makeWidget(self):
    '''
    Sub-class portion of SgField.makeWidget().
    '''

    return False

  def makeWidget(self):
    '''
    Creates the GUI widget for the field.

    If the widget already has been created this immediately returns.
    '''

    with self:
      if self.widget() != None:
        return True

      return self._makeWidget()

  def name(self):
    '''
    Returns the Shotgun API string used to reference the field on an Entity.
    '''

    return self.info().name()

  def parentEntity(self):
    '''
    Returns the parent SgEntity that the field is attached to.

    Fields only weakref their parent Entity so this may return None if the
    Entity has fallen out of scope.  You should always check if the returned
    result is None before doing anything.

    In the future fields may also be allowed to exist without an Entity so this
    may possibly return None.
    '''

    if self._parent == None:
      return None

    return self._parent()

  def returnType(self):
    '''
    Returns the SgEntity.RETURN_TYPE.
    '''

    return self.info().returnType()

  def setHasCommit(self, valid):
    '''
    Sets the commit state of the field to "valid".

    Note:
      Not thread safe!

    Args:
      * (bool) valid:
        Value of state.
    '''

    self.__hasCommit = bool(valid)

  def setHasSyncUpdate(self, valid):
    '''
    Sets the update state of the field to "valid".

    Note:
      Not thread safe!

    Args:
      * (bool) valid:
        Value of state.
    '''

    self.__hasSyncUpdate = bool(valid)

  def setIsCommitting(self, valid):
    '''
    Sets the commit state of the field to "valid".

    Note:
      Not thread safe!

    Args:
      * (bool) valid:
        Value of state.
    '''

    self._isCommitting = bool(valid)

  def setValid(self, valid):
    '''
    Sets the valid state of the field to "valid".

    Note:
      Not thread safe!

    Args:
      * (bool) valid:
        Value of state.
    '''

    self.__valid = bool(valid)

  def _setValue(self, sgData):
    '''
    Sub-class portion of SgField.setValue().

    Default function returns False.

    Note:
      Fields store their value in the property self._value.  Do not attempt to
      store the value for the field in another property on the class as SgField
      assumes this is the location of its value and other functions interact
      with it.

      Sub-classes only need to convert the incoming data to their internal
      format and return True.

      You should check if the incoming value is the same as the current value
      and return False without modfiying the fields value.

      valid() and hasCommit() are set based upon the return result of True/False.

    Args:
      * (dict) sgData:
        Dict of Shotgun formatted Entity field value.
    '''

    return False

  def setValue(self, sgData):
    '''
    Set the value of the field.

    Returns True on success.

    Args:
      * (object) sgData:
        New field value.
    '''

    with self:
      ShotgunORM.LoggerField.debug('%(sgField)s.setValue(...)', {'sgField': self})
      ShotgunORM.LoggerField.debug('    * sgData: %(sgData)s', {'sgData': sgData})

      if not self.isEditable():
        raise RuntimeError('%s is not editable!' % ShotgunORM.mkEntityFieldString(self))

      self.validate()

      if sgData == None:
        sgData = self.defaultValue()

      updateResult = self._setValue(sgData)

      if not updateResult:
        if not self.isValid():
          self.setValid(True)

        return False

      self.setValid(True)
      self.setHasCommit(True)

      self.changed()

      return True

  def setValueFromShotgun(self):
    '''
    Sets the fields value to its value in the Shotgun database.

    This sets isValid() to True and hasCommit() to False.  This will clear any
    previous modifications to the field.
    '''

    with self:
      ShotgunORM.LoggerField.debug('%(sgField)s.setValueFromShotgun()', {'sgField': self})

      self.invalidate()

      self._fromFieldData(self.valueSg())

      self.setValid(True)

      self.__profiler__.profile(self)

      self.changed()

      return True

  def setValueToDefault(self):
    '''
    Sets the fields value its default.

    This calls SgField.fromFieldData(self.defaultValue())

    Returns True on success.
    '''

    return self.setValue(self.defaultValue())

  def _toFieldData(self):
    '''
    Sub-class portion of SgField.toFieldData().
    '''

    return self._value

  def toFieldData(self):
    '''
    Returns the value of the Entity field formated for Shotgun.

    Note:
      In a multi-threaded env isValid() may be True however another thread may
      change / invalidate the field during the course of this function.  If
      you absolutely want to grab a valid value lock the Entity / field down
      before calling toFieldData.
    '''

    with self:
      self.validate()

      return self._toFieldData()

  def updateWidget(self):
    '''
    Tells the fields widget that it should update itself.
    '''

    widget = self.widget()

    if widget == None:
      return

    widget.update()

  def validate(self):
    '''
    Validates the field so that isValid() returns True.

    If the field has not yet pulled its value from Shotgun validate() will do
    the pull.

    Note:
      When isValid() is already True then this function returns immediately.
    '''

    with self:
      if self.isValid():
        return False

      ShotgunORM.LoggerField.debug('%(sgField)s.validate(curState=%(state)s)', {
        'sgField': self,
        'state': self.isValid()
      })

      self.__isUpdatingEvent.wait()

      # isSyncUpdating() might be True but if the search raised an exception it
      # didnt flag hasSyncUpdate() so fall back to just pulling from Shotgun
      # manually with setValueFromShotgun().
      if self.hasSyncUpdate():
        ShotgunORM.LoggerField.debug('    * hasSyncUpdate()')

        try:
          self._fromFieldData(self._updateValue)

          ShotgunORM.LoggerField.debug('        + Successful!')
        except:
          ShotgunORM.LoggerField.debug('        + Failed!')
        finally:
          self.setHasSyncUpdate(False)

          self._updateValue = None

        self.setValid(True)
        self.setHasCommit(False)

        self.changed()
      else:
        self.setValueFromShotgun()

      return True

  def _Value(self):
    '''
    Sub-class portion of SgField.value().

    This allows sub-classes to return a copy of their value so modifications
    can't be done to the internal value.

    Default returns SgField._value unchanged.
    '''

    return self._value

  def value(self):
    '''
    Returns the value of the Entity field.

    If the field has not yet been pulled from Shotgun it will call validate()
    which will pull the fields value before returning.
    '''

    with self:
      if self.isValid():
        return self._Value()

      self.validate()

      return self._Value()

  def _valueSg(self):
    '''
    Sub-class portion of SgField.valueSg().

    Sub-classes can override this function to define how to retrieve their value
    from Shotgun.

    Default function calls valueSg() on the parent Entity.

    For an example of a custom valueSg see the SgFieldSummary class.
    '''

    result = self.parentEntity().valuesSg([self.name()])

    if result.has_key(self.name()):
      return result[self.name()]
    else:
      return None

  def valueSg(self):
    '''
    Returns the fields value from Shotgun.
    '''

    ShotgunORM.LoggerField.debug('%(field)s.valueSg()', {'field': self})

    parent = self.parentEntity()

    if parent == None or not parent.exists():
      return None

    return self._valueSg()

  def validValues(self):
    '''
    Returns a list of valid values supported by the field.
    '''

    return self.info().validValues()

  def valueTypes(self):
    '''
    Returns a list of valid value types supported by the field.
    '''

    return self.info().valueTypes()

  def widget(self):
    '''
    Sub-classes can implement makeWidget so this returns some type of GUI widget
    for the field.

    Default returns None.
    '''

    with self:
      return self._widget

class SgUserField(SgField):
  '''
  A Class that represents a Shotgun Entity field.

  This field differs from SgField in that it does not represent a field which
  exists as part of an Entities schema.

  User fields are additional fields that can be added to an Entity that are not
  stored in the Shotgun database.

  A couple examples of a SgUserField are Entities "id" and "type" fields.  See
  SgFields.py.
  '''

  def hasCommit(self):
    '''
    This should always return False so that when an Entity is commited the value
    of this field is not added to the commit.
    '''

    return False

  def eventLogs(self, sgEventType=None, sgRecordLimit=0):
    '''
    Sub-classes can implement this to mimic event log Entities for the field.

    Default returns an empty list.

    Args:
      * (str) sgEventType:
        Event type filter such as "Shotgun_Asset_Change".

      * (int) sgRecordLimit:
        Limits the amount of returned events.
    '''

    return []

  def isCommittable(self):
    '''
    Returns False.
    '''

    return False

  def isQueryable(self):
    '''
    This should always return False because UserField objects do not represent
    fields in the Shotgun database.
    '''

    return False

  def lastEventLog(self, sgEventType=None):
    '''
    Sub-classes can implement this to mimic event log Entities for the field.

    Default returns None.

    Args:
      * (str) sgEventType:
        Event type filter such as "Shotgun_Asset_Change".
    '''

    return None

  def setHasCommit(self, valid):
    '''
    This should never set hasCommit() to True
    '''

    pass

  def setValueFromShotgun(self):
    '''
    Sub-classes can implement this to mimic setting the fields value from
    Shotgun.

    Default does nothing and returns False.
    '''

    return False

  def _valueSg(self):
    '''
    Sub-classes can implement this to mimic a pull from Shotgun.

    Default returns an empty dict.
    '''

    return {}

FIELD_RETURN_TYPES = {
  'unsupported': SgField.RETURN_TYPE_UNSUPPORTED,
  'checkbox': SgField.RETURN_TYPE_CHECKBOX,
  'color': SgField.RETURN_TYPE_COLOR,
  'color2': SgField.RETURN_TYPE_COLOR2,
  'currency': SgField.RETURN_TYPE_FLOAT,
  'date': SgField.RETURN_TYPE_DATE,
  'date_time': SgField.RETURN_TYPE_DATE_TIME,
  'duration': SgField.RETURN_TYPE_INT,
  'entity': SgField.RETURN_TYPE_ENTITY,
  'entity_type': SgField.RETURN_TYPE_LIST,
  'float': SgField.RETURN_TYPE_FLOAT,
  'image': SgField.RETURN_TYPE_IMAGE,
  'list': SgField.RETURN_TYPE_LIST,
  'multi_entity': SgField.RETURN_TYPE_MULTI_ENTITY,
  'password': SgField.RETURN_TYPE_TEXT,
  'percent': SgField.RETURN_TYPE_INT,
  'number': SgField.RETURN_TYPE_INT,
  'serializable': SgField.RETURN_TYPE_SERIALIZABLE,
  'status_list': SgField.RETURN_TYPE_STATUS_LIST,
  'summary': SgField.RETURN_TYPE_SUMMARY,
  'tag_list': SgField.RETURN_TYPE_TAG_LIST,
  'text': SgField.RETURN_TYPE_TEXT,
  'url': SgField.RETURN_TYPE_URL,
  'uuid': SgField.RETURN_TYPE_TEXT
}