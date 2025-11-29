defmodule TurretServer.PythonWorker do
  use GenServer
  require Logger

  # --- API ---
  def start_link(_) do
    GenServer.start_link(__MODULE__, nil, name: __MODULE__)
  end

  def process_frame(jpeg_binary) do
    GenServer.call(__MODULE__, {:process_frame, jpeg_binary}, 2000) # 0.2s timeout
  end

  # --- CALLBACKS ---
  @impl true
  def init(_) do
    # path to the worker where image processing happens
    script_path = "yolo_worker.py"

    # path to the VENV Python
    python_cmd = "env/bin/python3"

    # spawn a process using the python exec
    port = Port.open({:spawn, "#{python_cmd} -u #{script_path}"}, [:binary, {:packet, 4}])

    Logger.info("🐍 Python Worker Started (using venv)")
    {:ok, %{port: port, ready: true}}
  end

  @impl true
  def handle_call({:process_frame, _data}, _from, %{ready: false} = state) do
    {:reply, {:error, :not_ready}, state}
  end

  def handle_call({:process_frame, jpeg_data}, _from, %{port: port} = state) do
    Port.command(port, jpeg_data)

    # TODO: change to handle_cast to do it async
    receive do
      {^port, {:data, json_result}} ->
        decoded = Jason.decode!(json_result)
        {:reply, {:ok, decoded}, state}
    after
      1000 -> {:reply, {:error, :timeout}, state}
    end
  end

  @impl true
  def handle_info({_port, {:data, "READY"}}, state) do
    Logger.info("🐍 Python AI is READY for frames")
    {:noreply, %{state | ready: true}}
  end

  def handle_info(msg, state) do
    IO.inspect(msg, label: "received info:")
    {:noreply, state}
  end
end
