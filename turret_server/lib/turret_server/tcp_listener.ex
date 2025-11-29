defmodule TurretServer.TcpListener do
  use GenServer
  require Logger

  def start_link(port) do
    GenServer.start_link(__MODULE__, port, name: __MODULE__)
  end

  @impl true
  def init(port) do
    # Listen for TCP connections
    # :binary - receive as binaries
    # :packet, 4 - expects a 4-byte header telling us the size of the image
    # active: true - messages are sent to handle_info
    opts = [:binary, packet: 4, active: true, reuseaddr: true]
    {:ok, socket} = :gen_tcp.listen(port, opts)
    Logger.info("👂 Elixir TCP Server listening on #{port}")

    send(self(), :accept)
    {:ok, %{socket: socket, client: nil}}
  end

  @impl true
  def handle_info(:accept, state) do
    {:ok, client} = :gen_tcp.accept(state.socket)
    Logger.info("✅ Client Connected!")
    {:noreply, %{state | client: client}}
  end

  def handle_info({:tcp, _socket, jpeg_data}, state) do
    # send image to python worker
    case TurretServer.PythonWorker.process_frame(jpeg_data) do
      {:ok, detections} ->
        process_detections(detections, state.client)
      _ -> :ok
    end
    {:noreply, state}
  end

  def handle_info({:tcp_closed, _}, state) do
    Logger.info("❌ Client Disconnected")
    send(self(), :accept) # wait for connections
    {:noreply, %{state | client: nil}}
  end

  # --- LOGIC & COMMANDS ---
  defp process_detections([], _client), do: :ok
  defp process_detections([target | _], client) do
    # TODO Update logic: only convert Error X/Y to command
    err_x = target["err_x"]
    err_y = target["err_y"]

    cmd_pan = cond do
      err_x > 20 -> "RIGHT"
      err_x < -20 -> "LEFT"
      true -> "HOLD"
    end

    cmd_tilt = cond do
      err_y > 20 -> "DOWN"
      err_y < -20 -> "UP"
      true -> "HOLD"
    end

    if cmd_pan != "HOLD" or cmd_tilt != "HOLD" do
      Logger.info("🎯 #{target["label"]} | Err: #{err_x},#{err_y} | Cmd: #{cmd_pan}, #{cmd_tilt}")

      # send info back to pi
      response = Jason.encode!(%{pan: cmd_pan, tilt: cmd_tilt})
      :gen_tcp.send(client, response)
    end
  end
end
