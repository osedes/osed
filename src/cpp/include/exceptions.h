#ifndef EXCEPTIONS_H
#define EXCEPTIONS_H

#include <stdexcept>
#include <string>

namespace OSED
{
  class ParserException : public ::std::runtime_error
  {
  public:
    explicit ParserException(const ::std::string& msg) :
      ::std::runtime_error(msg) {};
    explicit ParserException(const char* msg) :
      ::std::runtime_error(msg) {};
  };

  class NoDescription : public ParserException {
    public:
      using ParserException::ParserException;
  };
  class UnknownNodeType : ParserException {
    public:
      using ParserException::ParserException;
  };
  class NullNotAllowed : ParserException {
    public:
      using ParserException::ParserException;
  };
  class UndefinedNotAllowed : ParserException {
    public:
      using ParserException::ParserException;
  };
  class StringNestedListString : ParserException {
    public:
      using ParserException::ParserException;
  };
} // namespace OSED

#endif // EXCEPTIONS_H
