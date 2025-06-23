#include <parser.h>
#include <exceptions.h>

#include <cassert>
#include <stdexcept>
#include <iostream>
#include <queue>

using namespace OSED;

Parser::Parser(const std::string& entity_yaml) :
  m_doc_(YAML::LoadFile(entity_yaml))
{
  assert(m_doc_.IsSequence());
  validate();
}

void Parser::validate() const
{
  validateEntities();
}

void Parser::validateEntities() const
{
  const auto& entities = m_doc_["entities"];
  assert(entities.IsSequence());
  for (const auto& entity : entities) {
    assert(entity.IsScalar());
    const auto& entity_name = entity.Scalar();
    const auto& entity_desc = m_doc_[entity_name];

    if (entity_desc) {
      validateNode(entity_desc);
    }
    // Neither universal nor particular
    else if (!(IsUniversal(entity_name) || IsParticular(entity_name))) {
      throw NoDescription("No description found for entity: " + entity_name);
    }
  }
}

void Parser::validateNode(const YAML::Node& node) const
{
  switch (node.Type()) {
  case YAML::NodeType::Null:
    validateNull(node);
    break;
  case YAML::NodeType::Scalar:
    validateScalar(node);
    break;
  case YAML::NodeType::Sequence:
    validateSequence(node);
    break;
  case YAML::NodeType::Map:
    validateMap(node);
    break;
  case YAML::NodeType::Undefined:
    validateUndefined(node);
    break;
  default:
    throw UnknownNodeType("Is there a YAML::NodeType not being handled !?");
  }
}

void Parser::validateSequence(const YAML::Node& node) const
{
  for (const auto& item : node) {
    validateNode(item);
  }
}

void Parser::validateMap(const YAML::Node& node) const
{
  for (const auto& item : node) {
    validateNode(item.second);
  }
}

bool Parser::isInNestedListOfStrings(
  const std::string& key,
  const YAML::Node& nested_list_str) const
{
  if(!nested_list_str) {
    return false;
  }

  std::queue<YAML::Node> Q;
  for(const auto& str_or_nested_list_str: nested_list_str) {
    Q.push(str_or_nested_list_str);
  }

  while (!Q.empty()) {
    const auto& str_or_nested_list_str = Q.front();
    Q.pop();

    const auto& node_t = str_or_nested_list_str.Type();

    switch (node_t) {
      case YAML::NodeType::Scalar:
        if (str_or_nested_list_str.Scalar() == key) {
          return true;
        }
        break;
      case YAML::NodeType::Sequence:
        for (const auto& item : str_or_nested_list_str) {
          Q.push(item);
        }
        break;
      case YAML::NodeType::Map:
        for (const auto& item : str_or_nested_list_str) {
          Q.push(item.second);
        }
        break;
      default:
        std::string msg = "items of `nested_list_str` must be strings";
        msg += " or nested list of strings";
        throw StringNestedListString(msg);
    }
  }

  return false;
}

const std::string Parser::NodeType(const YAML::Node& node) const
{
  switch (node.Type()) {
    case YAML::NodeType::Null:
      return "Null";
    case YAML::NodeType::Scalar:
      return "Scalar";
    case YAML::NodeType::Sequence:
      return "Sequence";
    case YAML::NodeType::Map:
      return "Map";
    case YAML::NodeType::Undefined:
      return "Undefined";
    default:
      return "Unknown";
  }
}
