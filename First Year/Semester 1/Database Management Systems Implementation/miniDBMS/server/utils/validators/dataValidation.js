function isValidDataType(type, length) {
  const validTypesWithLength = ['varchar', 'char'];
  if (validTypesWithLength.includes(type)) {
    return length && Number.isInteger(length) && length > 0;
  }

  const validTypes = ['int', 'float', 'bool', 'date'];
  return validTypes.includes(type);
}

function isValidColumnModifier(modifier) {
  const validModifiers = ['primary'];
  if (modifier.startsWith('foreign=')) {
    return true;
  }

  return validModifiers.includes(modifier.toLowerCase());
}

function isUnique(parts) {
  const uniqueIndex = parts.indexOf('unique');
  if (uniqueIndex === -1) return false;
  return uniqueIndex === parts.length - 1;
}

module.exports = {isValidDataType, isValidColumnModifier, isUnique};
