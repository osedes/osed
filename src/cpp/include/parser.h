#ifndef ENTITY_PARSER_H
#define ENTITY_PARSER_H

#include <exceptions.h>

#include <stack>

#include <yaml-cpp/yaml.h>

namespace OSED
{
  class Parser
  {
    private:
      YAML::Node m_doc_;
      std::stack<YAML::Node> m_stack_;

      void validate() const;
      void validateNode(const YAML::Node& node) const;
      inline void validateNull(const YAML::Node& node) const {
        throw NullNotAllowed("Null node is not allowed");};
      inline void validateUndefined(const YAML::Node& node) const {
        throw UndefinedNotAllowed("Undefined node is not allowed");};
      void validateEntities() const;
      inline void validateScalar(const YAML::Node& node) const {};
      void validateSequence(const YAML::Node& node) const;
      void validateMap(const YAML::Node& node) const;
      
      bool isInNestedListOfStrings(
        const std::string& key,
        const YAML::Node& nested_list_of_strings) const;

    public:
      Parser(const std::string& entity_yaml);

      inline const YAML::Node operator[](const std::string& key) const
      { return m_doc_[key]; };

      inline bool IsUniversal(const std::string& key) const
      {return isInNestedListOfStrings(key, m_doc_["universals"]);};

      inline bool IsParticular(const std::string& key) const
      {return isInNestedListOfStrings(key, m_doc_["particulars"]);};

      const std::string NodeType(const YAML::Node& node) const;

      inline const YAML::Node& GetDoc() const { return m_doc_; };
  };
 } // namespace OSED

#endif // ENTITY_PARSER_H
