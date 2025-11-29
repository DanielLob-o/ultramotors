defmodule TurretServerTest do
  use ExUnit.Case
  doctest TurretServer

  test "greets the world" do
    assert TurretServer.hello() == :world
  end
end
